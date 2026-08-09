"""`camera_zones` ustidagi VERSIYALANGAN yozuv va QAMROV so'rovi (AI-01, D-07/D-22).

=============================================================================
TAHRIR — `UPDATE` EMAS, YANGI QATOR (D-07).

`occupancy_events.zone_version` bir oy oldingi dalilning QAYSI kontur
bo'yicha o'lchanganini yozadi. Poligonni JOYIDA tahrirlash o'sha butun
tarixni RETROAKTIV qayta talqin qilardi: kechagi «band» hukmi bugungi
poligonga ko'chirilib, dalil rasmi bilan raqam bir-biriga mos kelmay
qolardi — va buni faqat nizo paytida, dalil qayta ko'rilganda sezish
mumkin bo'lardi.

Shuning uchun har o'zgargan zona uchun IKKI amal:

    eski qator:  is_active = false   (JOYIDA QOLADI, o'chirilmaydi)
    yangi qator: version   = eski + 1

Bu `tariffs` ning voris naqshi (MARKET-03) — o'sha yerda ham eski narx
qatoriga hech qachon tegilmaydi.

⚠ O'ZGARMAGAN ZONAGA TEGILMAYDI. Har `PUT` da butun kamerani qayta
  versiyalash tarixni shishirardi (bir kunda o'nlab versiya) va
  `zone_version` MA'NOSINI yo'qotardi: «qaysi kontur?» savoliga javob
  bir-biridan farq qilmaydigan yuzta qator bo'lardi.
=============================================================================

BUTUN KAMERA UCHUN ATOMAR (UI-SPEC §6.6).

`replace_for_camera()` — nomi aytganidek ALMASHTIRISH: yuborilgan ro'yxat
o'sha kameraning TO'LIQ holati. Ro'yxatda YO'Q faol zona `is_active=false`
bo'ladi.

⛔ QISMAN SAQLASH YO'Q va bu mahsulot qarori: yarim saqlangan kamera
   bandlik hisobini JIMGINA buzardi — bir qism rasta yangi kontur bilan,
   qolgani eskisi bilan o'lchanardi va hisobot baribir «to'liq» bo'lib
   ko'rinardi. Tranzaksiya chegarasi chaqiruvchida (`TenantSessionDep`).

=============================================================================
POYGA DB'GA TOPSHIRILADI — «AVVAL TEKSHIR, KEYIN YOZ» YOZILMAYDI.

`UNIQUE (market_id, camera_id, stall_id, version)` ikki bir vaqtdagi
saqlashdan birini `23505` bilan rad etadi va chaqiruvchi uni 409 ga
aylantiradi. Oldindan tekshirish ikki so'rovni bir xil bo'sh holatni
ko'rgan holda o'tkazib yuborardi va IKKALASI ham `version = 2` yozardi
(`nvr_repo.py::create_run()` da o'rnatilgan qoida va bir xil sabab).
=============================================================================

⛔ NISBAT FARQIDA AVTOMATIK TO'G'RILASH QILINMAYDI (§6.8). Kadr
   cho'zilganmi yoki kesilganmi — `source_width`/`source_height` dan bilib
   bo'lmaydi, ya'ni har qanday «tuzatish» taxmin bo'lardi. Noto'g'ri
   tuzatilgan zona esa aynan JIM NOSOZLIK: xato ko'rinmaydi, lekin
   boshqa maydon o'lchanadi. `needs_review_for_camera()` faqat FAKTNI
   qaytaradi — qarorni ODAM qabul qiladi.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final
from uuid import UUID

from sbozor_core.enums import StallStatus
from sbozor_core.models.market import Stall
from sbozor_core.models.nvr import Camera
from sbozor_core.models.occupancy import CameraZone
from sbozor_core.tenancy import TenantScopedRepository
from sqlalchemy import Select, and_, func, insert, select, update

from app.services.zone_geometry import aspect_ratio_matches

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "CameraZoneRepository",
    "CameraZoneRow",
    "ReplaceOutcome",
    "ZoneCoverage",
    "ZoneWrite",
    "zones_needing_review",
]


@dataclass(frozen=True, slots=True)
class CameraZoneRow:
    """Bitta zona qatori — javob shakli EMAS, repozitoriy chiqishi."""

    id: UUID
    camera_id: UUID
    stall_id: UUID
    stall_code: str
    """Rasta RAQAMI — zona ro'yxati uni `stall_id` bilan birga ko'rsatadi.

    UUID admin uchun hech nima anglatmaydi: (B) ro'yxatida u «14-A» ni
    ko'radi (UI-SPEC §6.4). Kodni javobga qo'shish `JOIN` ni bitta joyga
    yig'adi — aks holda frontend har zona uchun alohida so'rov yuborardi.
    """
    version: int
    polygon: list[Any]
    source_width: int
    source_height: int
    is_active: bool


@dataclass(frozen=True, slots=True)
class ZoneWrite:
    """Saqlanadigan zona — `PUT` tanasidan kelgan BITTA element.

    ⚠ `market_id` MAYDONI YO'Q va bo'lmaydi (T-05-24). U faqat
      `self.market_id` dan keladi, ya'ni so'rov tanasi uni hech qanday
      yo'l bilan boshqara olmaydi.

    ⚠ `version` MAYDONI HAM YO'Q: versiyani SERVER hisoblaydi. Klientga
      versiya yozishga ruxsat berish uni eski qator ustiga yozish
      imkonini berardi va D-07 ning butun kafolati klient xatosiga
      bog'lanib qolardi.
    """

    stall_id: UUID
    polygon: list[Any]
    source_width: int
    source_height: int


@dataclass(frozen=True, slots=True)
class ReplaceOutcome:
    """`replace_for_camera()` NIMA QILGANI — sanoqlar bilan.

    Javobga chiqmaydi; u jurnal va TESTLAR uchun. `unchanged` ayniqsa
    muhim: «ikkinchi marta bir xil poligon yangi versiya YARATMAYDI»
    da'vosi aynan shu son bilan o'lchanadi va u boshqa yo'l bilan
    ko'rinmasdi (qatorlar soni o'zgarmagani «hech nima yozilmadi» ni ham,
    «yozildi-yu, o'chirildi» ni ham anglatishi mumkin).
    """

    created: int
    versioned: int
    deactivated: int
    unchanged: int


@dataclass(frozen=True, slots=True)
class ZoneCoverage:
    """D-22 uchligi — `covered`, `uncovered`, `cameras_without_zones`.

    ⛔ `uncovered` HECH QACHON «bo'sh» DEB NOMLANMAYDI, na bu yerda, na
       javobda, na ekranda (G-15 copy darvozasi). Qamrovsiz rasta bo'sh
       EMAS — u haqida MA'LUMOT YO'Q, va bu farq mahsulotning yuragi:
       «bo'sh» deb hisoblangan qamrovsiz rasta hisobotda «to'lovsiz emas»
       bo'lib ko'rinardi, ya'ni tizim o'zi ko'rmagan narsani «joyida» deb
       e'lon qilardi.
    """

    covered: int
    uncovered: int
    cameras_without_zones: int


COVERAGE_STALL_STATUS: Final[str] = StallStatus.ACTIVE.value
"""Qamrov sanog'iga KIRADIGAN rasta holati — faqat `active`.

⚠ QARORNING SABABI BILLING KONTRAKTIDA, QULAYLIKDA EMAS.
  `StallStatus` docstringi (A4 taxmini): `closed` va `maintenance`
  rastalarga kunlik hisob YOZILMAYDI. Ya'ni ular uchun «qamrovdami?»
  savoli ma'nosiz — javob hisobga umuman ta'sir qilmaydi.

  Hamma rastani sanash `uncovered` ni HECH QACHON nolga tushmaydigan
  qilardi: foydalanishdan chiqarilgan har rasta abadiy «qamrovsiz»
  bo'lib turardi va admin bir necha oydan keyin bu ogohlantirishga
  qarashni butunlay to'xtatardi — ya'ni HAQIQIY qamrov teshigi shovqin
  ostida ko'milardi.
"""


def zones_needing_review(
    rows: Sequence[CameraZoneRow],
    current_width: int,
    current_height: int,
    *,
    tolerance: float,
) -> frozenset[UUID]:
    """Nisbati JORIY kadrnikidan farq qiladigan zonalarning `id` lari.

    ⚠ SOF FUNKSIYA VA U ATAYIN MODUL DARAJASIDA: `needs_review_for_camera()`
      ham, router ham AYNAN shu predikatdan foydalanadi. Ikki nusxa
      yozilganda `GET` javobidagi bayroq bilan repozitoriy qaytargan
      ro'yxat bir kun ajralib ketardi — admin ekranda «tekshirish kerak»
      ko'rmasdi, hisobot esa uni sanardi.

    `current_width`/`current_height` NOMA'LUM bo'lsa (kamerada hali
    yaroqli kadr yo'q) chaqiruvchi bu funksiyani UMUMAN chaqirmasligi
    kerak: nol o'lcham bilan `aspect_ratio_matches()` `False` beradi va
    BUTUN kamera «tekshirish kerak» bo'lib qolardi.
    """
    return frozenset(
        row.id
        for row in rows
        if not aspect_ratio_matches(
            row.source_width,
            row.source_height,
            current_width,
            current_height,
            tolerance=tolerance,
        )
    )


def _same_geometry(row: CameraZoneRow, wanted: ZoneWrite) -> bool:
    """Saqlangan zona yuborilgani bilan AYNAN bir xilmi.

    ⚠ POLIGON BILAN BIRGA KADR O'LCHAMI HAM SOLISHTIRILADI. Faqat
      poligonni solishtirish `source_width`/`source_height` ning
      o'zgarishini JIMGINA yutardi: koordinatalar bir xil, lekin ular
      endi BOSHQA kadrga nisbatan normalangan bo'lardi va nisbat
      darvozasi (§6.8) shu qatorni endi tekshirmasdi.

    `jsonb` dan qaytgan qiymat `list[list[float]]`, kirish esa
    `list[tuple[float, float]]` bo'lishi mumkin — shuning uchun ikkala
    tomon ham ro'yxat-ro'yxatga keltiriladi. `==` ni xom holda
    ishlatish `[[0.1, 0.2]] == [(0.1, 0.2)]` ni `False` qilardi va HAR
    saqlash yangi versiya yaratardi.
    """
    return (
        row.source_width == wanted.source_width
        and row.source_height == wanted.source_height
        and _as_points(row.polygon) == _as_points(wanted.polygon)
    )


def _as_points(polygon: Sequence[Any]) -> list[list[float]]:
    """Poligonni solishtirish uchun bitta shaklga keltiradi."""
    return [[float(value) for value in point] for point in polygon]


class CameraZoneRepository(TenantScopedRepository):
    """`camera_zones` ustidagi CRUD, versiyalash va qamrov."""

    # ------------------------------------------------------------------
    # O'qish
    # ------------------------------------------------------------------

    def _rows(self) -> Select[Any]:
        """Zona + rasta raqami so'rovining YAGONA ta'rifi.

        Birikma sharti `market_id` ni ham o'z ichiga oladi: kompozit kalit
        bo'yicha birikish tenant invariantining bir qismi, `scoped()` esa
        faqat ASOSIY entity'ga predikat qo'shadi
        (`stall_repo.py::ZoneRepository._rows()` da o'rnatilgan qoida).

        `INNER JOIN` — rasta MAJBURIY (`stall_id NOT NULL` + kompozit FK),
        ya'ni `LEFT JOIN` hech qachon boshqa natija bermasdi-yu, `NULL`
        holatini boshqarish uchun o'lik kod talab qilardi.
        """
        return self.scoped(
            select(
                CameraZone.id,
                CameraZone.camera_id,
                CameraZone.stall_id,
                Stall.code.label("stall_code"),
                CameraZone.version,
                CameraZone.polygon,
                CameraZone.source_width,
                CameraZone.source_height,
                CameraZone.is_active,
            ).join(
                Stall,
                and_(Stall.market_id == CameraZone.market_id, Stall.id == CameraZone.stall_id),
            )
        )

    async def list_for_camera(
        self, camera_id: UUID, *, include_inactive: bool = False
    ) -> list[CameraZoneRow]:
        """Kameraning zonalari, rasta raqami tartibida.

        ⚠ STANDART HOLATDA FAQAT FAOL ZONALAR. Eskirgan versiyalar
          jadvalda QOLADI (D-07) va vaqt o'tgani sari ular faollardan
          ko'p bo'ladi — ularni standart javobga qo'shish muharrirni
          bir rastaga o'nlab poligon chizardi.

        `include_inactive=True` — tarix yuzasi (UI-SPEC §6.6 dagi
        «Oldingi versiyalar» bloki). U `ix_camera_zones_active` qisman
        indeksiga TUSHMAYDI va bu kutilgan: tarix so'rovi kamdan-kam
        chaqiriladi.
        """
        stmt = self._rows().where(CameraZone.camera_id == camera_id)
        if not include_inactive:
            stmt = stmt.where(CameraZone.is_active.is_(True))

        result = await self.session.execute(
            stmt.order_by(Stall.code_sort, CameraZone.version.desc())
        )
        return [_row(record) for record in result]

    async def camera_exists(self, camera_id: UUID) -> bool:
        """Kamera SHU bozorda bormi.

        ⛔ ZONA RO'YXATI BO'SHLIGI BILAN ADASHTIRMANG — aynan shuning
           uchun bu alohida so'rov. Begona bozorning `camera_id` si bilan
           `list_for_camera()` 0 qator beradi va u «zonasi yo'q kamera»
           dan farq qilmaydi. Chaqiruvchi ikkalasini ajratishi SHART:
           birinchisi 404, ikkinchisi bo'sh 200.

        ⚠ ARXIVLANGAN KAMERA HAM MAVJUD deb hisoblanadi (D-10: qator hech
          qachon o'chirilmaydi) va uning zonalari TAHRIRLANISHI ham
          mumkin. Yozishni bloklash yangi xato kodi talab qilardi,
          foydasi esa nol: arxivlangan kameradan kadr kelmaydi, ya'ni
          uning zonasi hech qanday bandlik hodisasi tug'dirmaydi. Qamrov
          sanog'ida (`coverage()`) esa u ATAYIN chiqarib tashlanadi.
        """
        result = await self.session.execute(
            self.scoped(select(Camera.id).where(Camera.id == camera_id))
        )
        return result.scalar_one_or_none() is not None

    async def needs_review_for_camera(
        self,
        camera_id: UUID,
        current_width: int,
        current_height: int,
        *,
        tolerance: float,
    ) -> frozenset[UUID]:
        """Joriy kadr nisbatiga MOS KELMAYDIGAN faol zonalar (§6.8).

        ⛔ AVTOMATIK TO'G'RILASH QILINMAYDI — modul docstringiga qarang.
           Bu metod FAKT qaytaradi va boshqa hech nima qilmaydi.
        """
        rows = await self.list_for_camera(camera_id)
        return zones_needing_review(rows, current_width, current_height, tolerance=tolerance)

    # ------------------------------------------------------------------
    # Yozuv — VERSIYALANGAN va BUTUN KAMERA UCHUN ATOMAR
    # ------------------------------------------------------------------

    async def replace_for_camera(
        self, camera_id: UUID, zones: Sequence[ZoneWrite]
    ) -> ReplaceOutcome:
        """Kameraning zonalarini ALMASHTIRADI (D-07 versiyalash bilan).

        Uch tarmoq, har biri bir xil qoidadan kelib chiqadi («tarix qayta
        yozilmaydi»):

            faol qator YO'Q            -> yangi qator, `version = MAX + 1`
            faol qator BOR, geometriya bir xil -> TEGILMAYDI
            faol qator BOR, geometriya boshqa  -> eskisi `is_active=false`,
                                                  yangisi `version = MAX + 1`

        Yuborilgan ro'yxatda YO'Q faol zona `is_active=false` bo'ladi —
        `PUT` ning ALMASHTIRISH semantikasi (UI-SPEC §6.6).

        ⚠ `version` FAOL qatordan emas, SHU (kamera, rasta) juftining
          BARCHA qatorlaridan olingan MAKSIMUMDAN hisoblanadi. Faoldan
          olish o'chirilib qayta chizilgan zonada eski versiya raqamini
          QAYTA ISHLATARDI va `UNIQUE (market_id, camera_id, stall_id,
          version)` uni `23505` bilan rad etardi — admin esa sababsiz
          «konflikt» ko'rardi.

        Raises:
            IntegrityError: bir vaqtda ikkinchi saqlash ketgan bo'lsa
                (`23505`). Chaqiruvchi uni 409 ga aylantiradi; oldindan
                tekshiruv ATAYIN yozilmagan (modul docstringi).
        """
        active = {row.stall_id: row for row in await self.list_for_camera(camera_id)}
        next_versions = await self._next_versions(camera_id)

        created = versioned = deactivated = unchanged = 0

        for wanted in zones:
            current = active.pop(wanted.stall_id, None)

            if current is not None and _same_geometry(current, wanted):
                unchanged += 1
                continue

            if current is not None:
                await self._deactivate(current.id)
                versioned += 1
            else:
                created += 1

            await self._insert(
                camera_id,
                wanted,
                version=next_versions.get(wanted.stall_id, 0) + 1,
            )

        # Ro'yxatda qolmagan faol zonalar — ALMASHTIRISHNING o'chirish yarmi.
        for orphan in active.values():
            await self._deactivate(orphan.id)
            deactivated += 1

        return ReplaceOutcome(
            created=created,
            versioned=versioned,
            deactivated=deactivated,
            unchanged=unchanged,
        )

    async def deactivate(self, zone_id: UUID) -> bool:
        """Bitta zonani eskirgan deb belgilaydi; topilmasa `False`.

        ⛔ QATTIQ `DELETE` YO'Q va bu jadval darajasidagi qaror:
           `occupancy_events` `(market_id, camera_zone_id)` ga kompozit FK
           bilan tayanadi, ya'ni qatorni o'chirish o'tmishdagi BUTUN
           dalil zanjirini uzardi (yoki FK uni bloklardi va admin
           tushunarsiz 409 olardi). `cameras.is_archived` bilan aynan bir
           xil qaror.

        `UPDATE ... RETURNING` ikki ishni birga bajaradi: «bor edimi?»
        savoliga javob beradi va yozadi. Avval `SELECT`, keyin `UPDATE`
        qilinsa ikkalasi orasida qator o'zgarishi mumkin edi.

        ⚠ `is_active = true` sharti MAJBURIY: usiz allaqachon eskirgan
          qatorni ikkinchi marta «o'chirish» 204 qaytarardi, ya'ni
          `DELETE` idempotent ko'rinardi-yu, aslida `updated_at` ni
          har chaqiruvda o'zgartirib, auditga soxta qator yozardi.
        """
        return await self._deactivate(zone_id)

    async def _deactivate(self, zone_id: UUID) -> bool:
        result = await self.session.execute(
            update(CameraZone)
            .where(
                CameraZone.market_id == self.market_id,
                CameraZone.id == zone_id,
                CameraZone.is_active.is_(True),
            )
            .values(is_active=False)
            .returning(CameraZone.id)
        )
        return result.scalar_one_or_none() is not None

    async def _insert(self, camera_id: UUID, zone: ZoneWrite, *, version: int) -> UUID:
        """Yangi versiya qatorini yozadi.

        `market_id` `self.market_id` DAN — so'rov tanasidan EMAS
        (T-05-24, mass-assignment darvozasi).
        """
        result = await self.session.execute(
            insert(CameraZone)
            .values(
                market_id=self.market_id,
                camera_id=camera_id,
                stall_id=zone.stall_id,
                version=version,
                polygon=_as_points(zone.polygon),
                source_width=zone.source_width,
                source_height=zone.source_height,
                is_active=True,
            )
            .returning(CameraZone.id)
        )
        return result.scalar_one()

    async def _next_versions(self, camera_id: UUID) -> dict[UUID, int]:
        """(rasta -> shu kameradagi ENG KATTA versiya), FAOLLIKDAN QAT'I NAZAR.

        Eskirgan qatorlar ham sanoqqa kiradi — sabab `replace_for_camera()`
        docstringidagi ⚠ bandida.
        """
        result = await self.session.execute(
            self.scoped(
                select(CameraZone.stall_id, func.max(CameraZone.version).label("top"))
                .where(CameraZone.camera_id == camera_id)
                .group_by(CameraZone.stall_id)
            )
        )
        return {record.stall_id: int(record.top) for record in result}

    # ------------------------------------------------------------------
    # Qamrov (D-22)
    # ------------------------------------------------------------------

    async def coverage(self) -> ZoneCoverage:
        """`covered` / `uncovered` / `cameras_without_zones` uchligi.

        ⚠ `market_id` ARGUMENT SIFATIDA OLINMAYDI (reja imzosidan farq)
          — u `self.market_id` da va u YAGONA manba. Ikkinchi argument
          chaqiruvchiga boshqa bozorning identifikatorini berish yo'lini
          ochardi va u aynan T-05-24 ning shakli bo'lardi.

        ⚠ UCHALA SON HAM HAR DOIM QAYTADI, nol bo'lganda ham (UI-SPEC
          §6.9). «Nol bo'lsa ko'rsatmaslik» tabiiy ko'rinadi va aynan
          jim yiqilishni tug'dirardi: birorta zona chizilmagan bozorda
          qamrov kartasi UMUMAN chiqmasdi va admin «hammasi joyida» deb
          o'qirdi.

        Uchta alohida so'rov, bitta emas: `covered`/`uncovered` RASTA
        bo'yicha, `cameras_without_zones` esa KAMERA bo'yicha sanaydi.
        Ularni bitta `JOIN` ga yig'ish dekart ko'paytmasi berardi va
        sonlar bir-birini ko'paytirardi.

        ⚠ `scoped()` BU YERDA ISHLATILMAYDI va sabab mexanik: u
          so'rovning ASOSIY entity'sidan `market_id` ustunini oladi,
          `select(func.count(...))` da esa entity YO'Q va u `TypeError`
          ko'taradi (`TenantScopedRepository.scoped()` docstringidagi
          aynan shu holat). Shuning uchun predikat QO'LDA yoziladi —
          uni tushirib qoldirish MUMKIN EMAS, chunki har uch so'rovda u
          boshqa shartlar bilan bir qatorda turibdi va RLS ikkinchi
          qatlam bo'lib qoladi.
        """
        covered_stalls = (
            select(CameraZone.stall_id)
            .where(
                CameraZone.market_id == self.market_id,
                CameraZone.is_active.is_(True),
            )
            .distinct()
            .scalar_subquery()
        )

        total = await self.session.execute(
            select(func.count(Stall.id)).where(
                Stall.market_id == self.market_id,
                Stall.status == COVERAGE_STALL_STATUS,
            )
        )
        covered = await self.session.execute(
            select(func.count(Stall.id)).where(
                Stall.market_id == self.market_id,
                Stall.status == COVERAGE_STALL_STATUS,
                Stall.id.in_(covered_stalls),
            )
        )
        # ⚠ ARXIVLANGAN KAMERA SANOQQA KIRMAYDI: admin uni ATAYIN
        #   ishlatmaydigan qilgan (D-10), ya'ni unga zona chizish talab
        #   qilish adminni o'zi qabul qilgan qarorga qarshi ogohlantirardi.
        cameras = await self.session.execute(
            select(func.count(Camera.id)).where(
                Camera.market_id == self.market_id,
                Camera.is_archived.is_(False),
                Camera.id.notin_(
                    select(CameraZone.camera_id)
                    .where(
                        CameraZone.market_id == self.market_id,
                        CameraZone.is_active.is_(True),
                    )
                    .distinct()
                    .scalar_subquery()
                ),
            )
        )

        total_count = int(total.scalar_one())
        covered_count = int(covered.scalar_one())
        return ZoneCoverage(
            covered=covered_count,
            uncovered=total_count - covered_count,
            cameras_without_zones=int(cameras.scalar_one()),
        )


def _row(record: Any) -> CameraZoneRow:
    return CameraZoneRow(
        id=record.id,
        camera_id=record.camera_id,
        stall_id=record.stall_id,
        stall_code=record.stall_code,
        version=int(record.version),
        polygon=list(record.polygon),
        source_width=int(record.source_width),
        source_height=int(record.source_height),
        is_active=bool(record.is_active),
    )
