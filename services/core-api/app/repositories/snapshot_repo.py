"""Kadr metama'lumoti — dalil zanjirining birinchi halqasi (CAM-06/CAM-07).

=============================================================================
1-QOIDA: QATOR HECH QACHON O'CHIRILMAYDI.

Obyekt omborda o'chiriladi, QATOR esa qoladi va «kadr mavjud edi,
arxivdan `<sana>` da chiqarildi» deb HALOL ko'rsatiladi
(`04-RESEARCH.md` §D.10).

Sabab 6-fazada: `daily_charges` dalil-kadrlarga bog'lanadi (BILL-02) va
qatorni yo'q qilish hisob yozuvining dalil havolasini UZARDI. O'shanda
«bu rasta o'sha kuni band edi» degan da'vo rasm-asossiz qolardi va hisob
bahsli bo'lganda uni himoya qiladigan hech narsa bo'lmasdi.

Bu sinfda qator olib tashlaydigan metod UMUMAN YOZILMAGAN. Uning
YO'QLIGI kelishuv emas, STRUKTURA (`app/services/go2rtc.py:193-197`
uslubi): metod bo'lmasa uni chaqirib bo'lmaydi, konventsiya esa
unutiladi.

⚠ TAQIQ `schedule_repo.delete_future()` GA TARQALMAYDI va bu ZIDDIYAT
  EMAS: hali boshlanmagan profil birorta `capture_runs` qatorini
  tug'dirmagan, ya'ni o'chiriladigan DALIL yo'q. Bu yerdagi har bir qator
  esa MAVJUD BO'LGAN kadrning yagona yozuvi.
=============================================================================

=============================================================================
2-QOIDA: `is_billable` O'ZGARTIRILMAYDI — `purged` bo'lgan kadr uchun ham.

Ustun `GENERATED ALWAYS AS (quality_verdict = 'ok') STORED`, ya'ni ilova
unga TEXNIK jihatdan ham yoza olmaydi (D-16). Lekin qoidaning MAZMUNI
texnikadan kengroq: o'sha paytda qilingan hisob RETROAKTIV bekor
qilinmaydi. Kadr arxivdan chiqarilgani uning o'sha kuni yaroqli
BO'LGANINI o'zgartirmaydi.

`retention` faqat IKKI ustunga tegadi: `storage_tier` va
`object_deleted_at` (+ siqilgandan keyin `size_bytes`).
=============================================================================

=============================================================================
3-QOIDA: HOLAT O'TISHI BIR YO'NALISHLI VA U PREDIKAT BILAN QULFLANGAN.

    full  ->  compressed  ->  purged
    full  ---------------->  purged

`retention_candidates()` va `mark_compressed()` da `storage_tier` QAT'IY
predikat, ya'ni ikki marta siqish STRUKTURAVIY ravishda mumkin emas.
Sabab fizik: JPEG qayta kodlash YO'QOTISHLI va avlod yo'qotishi TO'PLANADI
— ikki marta siqilgan kadr bir yildan keyin dalil sifatida o'qib bo'lmas
holga kelardi (T-04-37). «Ehtiyot uchun yana bir marta yugurtiraylik»
degan operatsion refleks aynan shu predikatga urilib to'xtaydi.

Noto'g'ri holatdagi qator JIMGINA o'zgarmaydi va chaqiruvchi buni
`False` dan biladi (`nvr_repo.start_run` bilan bir xil shakl).
=============================================================================

=============================================================================
4-QOIDA: AVVAL S3 `PUT`, KEYIN BU QATOR (§B.4).

    1. kadr olish        -> baytlar xotirada
    2. sifat tahlili     -> sof funksiya (`quality.py`)
    3. S3 `PUT`          -> DETERMINISTIK kalit (`object_key.py`)
    4. `record()` + `capture_repo.finish_succeeded()`  -> BITTA tranzaksiya

QATOR OBYEKT BORLIGINI TASDIQLAYDI. Teskari tartib 6-fazaga MAVJUD
BO'LMAGAN dalilga havola berardi va BILL-02 («har hisob dalil-kadrlarga
bog'langan») aynan buni ko'tara olmaydi.

⚠ Bu repozitoriy TARTIBNI MAJBURLAY OLMAYDI — u S3 ni umuman ko'rmaydi.
  Shuning uchun qoida shu yerda CHAQIRUVCHIGA aniq aytiladi va uni
  `04-06`/`04-07` bajaradi. Yetim obyekt (3 bajarildi, 4 bajarilmadi)
  MUMKIN va u MUAMMO EMAS: kalit deterministik bo'lgani uchun uni topish
  arzon va kunlik supurgi uni tozalaydi.
=============================================================================

TENANT FILTRI IKKI QATLAM: RLS policy'si himoya to'ri, `market_id`
predikati esa aniq filtr (`sbozor_core/tenancy.py`).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sbozor_core.enums import SnapshotTier
from sbozor_core.models import CaptureRun, Snapshot
from sbozor_core.tenancy import TenantScopedRepository
from sqlalchemy import func, insert, select, update

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "COMPRESSIBLE_TIER",
    "PURGEABLE_TIERS",
    "RetentionCandidate",
    "SnapshotMeasurementMissingError",
    "SnapshotRepository",
]

COMPRESSIBLE_TIER: str = SnapshotTier.FULL.value
"""Siqish MANBAI — faqat `full`. Enum a'zosidan HOSILA, literal EMAS.

Modul docstringidagi 3-qoidaning mexanizmi: `compressed` qator bu
predikatga tushmaydi, ya'ni uni ikkinchi marta siqib bo'lmaydi.
"""

PURGEABLE_TIERS: tuple[str, ...] = (SnapshotTier.FULL.value, SnapshotTier.COMPRESSED.value)
"""Obyekti o'chirilishi mumkin bo'lgan qatlamlar — `purged` ular orasida YO'Q.

⚠ `full` HAM shu ro'yxatda va bu ATAYIN: siqish bosqichini o'tkazib
  yuborgan (yoki siqish o'chirilgan) kadr ham 455 kundan keyin arxivdan
  chiqarilishi kerak. Faqat `compressed` ni qoldirish `retention_full_days`
  ni `0` qilib qo'ygan bozorda kadrlarni MANGU saqlab qolardi.
"""


class SnapshotMeasurementMissingError(ValueError):
    """`quality_mean`/`quality_stddev` `None` bo'lib keldi — SXEMA CHEGARASI.

    ⛔ BU IKKI REJANING O'ZARO ZID QARORI VA U SHU YERDA OCHIQ AYTILADI.

    `04-03` (sxema) `snapshots.quality_mean` va `quality_stddev` ni
    `NOT NULL` qilib yozgan. `04-04` (sof modul) esa `corrupt` kadr uchun
    o'lchovlarni `None` qaytaradi va buni ATAYIN qilgan: nol qiymat
    «o'lchandi va nol chiqdi» ma'nosini berardi va D-15 ning
    `percentile_cont` bilan chegara chiqarish yo'lini buzardi.

    Ya'ni `corrupt` verdiktli kadrni bu jadvalga YOZIB BO'LMAYDI. Ikki
    to'g'ri yechim bor va ikkalasi ham SHU REJADAN TASHQARIDA:

      (a) `corrupt` kadr `snapshots` ga umuman YOZILMAYDI — u
          `capture_repo.finish_failed(capture_invalid_response)` bilan
          yopiladi. Xato reyestrida bu kod AYNAN shu holat uchun bor
          («Javob keldi, lekin ichida TASVIR YO'Q»), ya'ni taksonomiyaning
          O'Z dizayni shu yo'lni ko'rsatadi.

      (b) Migratsiya uchala `quality_*` ustunini NULLABLE qiladi — u holda
          `04-UI-SPEC.md` §6.4 dagi C4 hujayrasi («Buzuq» = `succeeded` +
          `corrupt`) haqiqatan mumkin bo'ladi.

    (a) va (b) BIR VAQTDA to'g'ri bo'la olmaydi: birinchisida C4 hujayrasi
    HECH QACHON chizilmaydi, ikkinchisida esa `capture_invalid_response`
    kodi ishlatilmaydi. Qarorni `04-07` (kadr olish oqimi) qabul qiladi —
    u ikkala yuzani ham ko'radigan birinchi reja.

    Bu istisno o'sha qarorni ERTA va ANIQ joyda ko'rsatadi. Usiz nosozlik
    `NotNullViolation` bo'lib worker ichida, birinchi buzuq kadrda —
    ya'ni ehtimol ertalabki 06:00 slotida — chiqardi va xabar hech nimani
    tushuntirmasdi.
    """


@dataclass(frozen=True, slots=True)
class RetentionCandidate:
    """Retention jobi uchun BITTA qator — obyektni topish uchun yetarli minimum.

    Butun `Snapshot` obyekti QAYTARILMAYDI: job partiya bilan ishlaydi
    (`retention_batch_size` standarti 200) va har bir obyektga
    o'n beshta ustun olib kelish tarmoqni bekorga bandi qilardi. Kerak
    bo'lgani — `object_key` (S3 uchun) va `id` (holatni yangilash uchun).

    `size_bytes` diagnostika uchun: siqishdan oldin va keyin taqqoslash
    «siqish HAQIQATAN ishladimi?» savoliga javob beradi.
    """

    id: UUID
    object_key: str
    business_date: date
    size_bytes: int
    storage_tier: str


class SnapshotRepository(TenantScopedRepository):
    """`snapshots` ustidagi yozish, o'qish va retention holat o'tishlari.

    ⛔ QATOR OLIB TASHLAYDIGAN METOD YO'Q — modul docstringidagi 1-qoida.
    """

    # ------------------------------------------------------------------
    # Yozish — dalil zanjirining boshi
    # ------------------------------------------------------------------

    async def record(
        self,
        *,
        capture_run_id: UUID,
        camera_id: UUID,
        scheduled_at: datetime,
        captured_at: datetime,
        slot_time: time,
        object_key: str,
        size_bytes: int,
        quality_verdict: str,
        quality_mean: float | None,
        quality_stddev: float | None,
        quality_saturation: float | None,
        quality_thresholds_version: int,
        light_mode: str,
        capture_method: str,
        etag: str | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> UUID:
        """Kadr yozuvini yaratadi va uni `capture_runs` ga BOG'LAYDI.

        ⚠ AVVAL S3 `PUT`, KEYIN BU CHAQIRUV — modul docstringidagi
          4-qoida. Bu qator obyekt BORLIGINI tasdiqlaydi.

        ⚠ HAVOLA SHU YERDA YOZILADI (`capture_runs.snapshot_id`), garchi
          `capture_repo.finish_succeeded()` uni QAYTA ham yozsa. Takror
          ATAYIN: bitta `UPDATE` narxiga kadr HECH QACHON o'z yugurishidan
          uzilgan holda qolmaydi — chaqiruvchi `finish_succeeded()` ni
          unutса ham qator `succeeded` bo'lmaydi, LEKIN havola joyida
          bo'ladi va dalil topiladigan qoladi.

        ⚠ `scheduled_at` `capture_runs` DAN NUSXALANADI, mustaqil
          hisoblanmaydi (`models/snapshot.py::SNAPSHOT_BUSINESS_DATE_EXPR`).
          Ikki mustaqil hisoblash manbai yarim tunda bir kun farq qilardi
          va kadr `capture_runs` da bir kunga, `snapshots` da BOSHQA kunga
          tushardi — 6-faza esa dalilni `business_date` bo'yicha izlaydi.

        ⚠ `business_date` va `is_billable` ARGUMENT EMAS: ikkalasi ham
          `GENERATED` ustun. `is_billable` `quality_verdict = 'ok'` dan
          hosil bo'ladi, ya'ni `dark` kadr uchun u `False` va uni ilova
          qatlamidan ko'tarib bo'lmaydi (D-16).

        Raises:
            SnapshotMeasurementMissingError: o'lchov `None` bo'lsa — o'sha
                sinf docstringidagi ikki rejaning zid qarorini o'qing.
            IntegrityError: shu `capture_run_id` uchun ikkinchi kadr
                (`uq_snapshots_market_id_capture_run_id`, `23505`) yoki
                takroriy `object_key`. Chaqiruvchi uni 409 ga aylantiradi;
                ikkinchi kadr «qaysi biri dalil?» savolini javobsiz
                qoldirardi va 5-faza tasodifiy birini tanlardi.
        """
        if quality_mean is None or quality_stddev is None:
            raise SnapshotMeasurementMissingError(
                f"quality_verdict={quality_verdict!r} uchun o'lchovlar yo'q "
                f"(mean={quality_mean}, stddev={quality_stddev}), lekin "
                "`snapshots.quality_mean`/`quality_stddev` NOT NULL. "
                "Yechim `SnapshotMeasurementMissingError` docstringida — "
                "qarorni 04-07 qabul qiladi."
            )

        result = await self.session.execute(
            insert(Snapshot)
            .values(
                # `market_id` REPOZITORIYDAN, argumentdan EMAS
                # (mass-assignment darvozasi — `nvr_repo` bilan bir xil qoida).
                market_id=self.market_id,
                capture_run_id=capture_run_id,
                camera_id=camera_id,
                scheduled_at=scheduled_at,
                captured_at=captured_at,
                slot_time=slot_time,
                object_key=object_key,
                size_bytes=size_bytes,
                etag=etag,
                width=width,
                height=height,
                quality_verdict=quality_verdict,
                quality_mean=_as_numeric(quality_mean),
                quality_stddev=_as_numeric(quality_stddev),
                quality_saturation=_as_numeric(quality_saturation),
                quality_thresholds_version=quality_thresholds_version,
                light_mode=light_mode,
                capture_method=capture_method,
            )
            .returning(Snapshot.id)
        )
        snapshot_id: UUID = result.scalar_one()

        await self.session.execute(
            update(CaptureRun)
            .where(
                CaptureRun.market_id == self.market_id,
                CaptureRun.id == capture_run_id,
            )
            .values(snapshot_id=snapshot_id)
        )
        return snapshot_id

    # ------------------------------------------------------------------
    # O'qish
    # ------------------------------------------------------------------

    async def get(self, snapshot_id: UUID) -> Snapshot | None:
        """Bitta kadr yozuvi yoki `None` (topilmadi / begona bozorniki -> 404).

        `purged` qator ham QAYTADI va bu ATAYIN: «kadr mavjud edi,
        arxivdan chiqarildi» javobi «bunday kadr yo'q» dan butunlay boshqa
        ma'no. Ikkinchisi operatorni yo'qolgan dalil qidirishga
        yuborardi.
        """
        result = await self.session.execute(
            self.scoped(select(Snapshot)).where(Snapshot.id == snapshot_id)
        )
        return result.scalar_one_or_none()

    async def retention_candidates(
        self, *, older_than: date, tier: str, limit: int
    ) -> Sequence[RetentionCandidate]:
        """Retention siyosatiga tushgan kadrlar — partiya bilan.

        ⛔ `tier` QAT'IY PREDIKAT — modul docstringidagi 3-qoida. `full`
           so'ralganda `compressed` qatorlar natijaga TUSHMAYDI, ya'ni
           ikkinchi marta siqish strukturaviy ravishda mumkin emas.

        ⚠ `business_date` bo'yicha, `created_at` bo'yicha EMAS: siyosat
          «kadr QAYSI KUNGA tegishli» ga bog'liq, «qachon yozilgan» ga
          emas. Kechikib yozilgan kadr (qayta urinish, migratsiya) aks
          holda o'z tengdoshlaridan keyinroq o'chirilardi.

        Args:
            older_than: shu sanadan OLDINGI biznes-kunlar (chegara O'ZI
                kirmaydi).
            tier: `SnapshotTier` qiymati — `COMPRESSIBLE_TIER` yoki
                `PURGEABLE_TIERS` dan biri.
            limit: partiya hajmi (`retention_batch_size`).
        """
        result = await self.session.execute(
            self.scoped(
                select(
                    Snapshot.id,
                    Snapshot.object_key,
                    Snapshot.business_date,
                    Snapshot.size_bytes,
                    Snapshot.storage_tier,
                )
                .where(
                    Snapshot.storage_tier == tier,
                    Snapshot.business_date < older_than,
                )
                .order_by(Snapshot.business_date, Snapshot.id)
                .limit(limit)
            )
        )
        return [
            RetentionCandidate(
                id=row.id,
                object_key=row.object_key,
                business_date=row.business_date,
                size_bytes=row.size_bytes,
                storage_tier=row.storage_tier,
            )
            for row in result
        ]

    # ------------------------------------------------------------------
    # Retention — BIR YO'NALISHLI holat o'tishlari
    # ------------------------------------------------------------------

    async def mark_compressed(self, snapshot_id: UUID, *, size_bytes: int) -> bool:
        """`full` -> `compressed` va yangi hajm.

        ⛔ `storage_tier = 'full'` SHARTI DARVOZA, TOZALIK EMAS. U bo'lmasa
           qayta yugurtirilgan retention jobi allaqachon siqilgan kadrni
           IKKINCHI marta siqardi va avlod yo'qotishi to'planardi
           (T-04-37).

        ⚠ `object_key` O'ZGARMAYDI — siqilgan versiya AYNAN o'sha kalitni
          USTIGA yozadi. Shuning uchun 6-fazadagi dalil havolalari hech
          qachon buzilmaydi va bu yerda yangilanadigan yagona qiymat —
          hajm.

        Returns:
            Qator `full` holatda topilib o'tgan bo'lsa `True`. `False` —
            qator yo'q, allaqachon siqilgan/o'chirilgan yoki begona
            bozorniki.
        """
        result = await self.session.execute(
            update(Snapshot)
            .where(
                Snapshot.market_id == self.market_id,
                Snapshot.id == snapshot_id,
                Snapshot.storage_tier == COMPRESSIBLE_TIER,
            )
            .values(storage_tier=SnapshotTier.COMPRESSED.value, size_bytes=size_bytes)
            .returning(Snapshot.id)
        )
        return result.scalar_one_or_none() is not None

    async def mark_purged(self, snapshot_id: UUID) -> bool:
        """Obyekt arxivdan chiqarildi: `storage_tier='purged'` + vaqt tamg'asi.

        ⛔ QATOR QOLADI — modul docstringidagi 1-qoida. Bu metod FAQAT
           ikkita ustunni o'zgartiradi.

        ⛔ `is_billable` GA TEGILMAYDI (2-qoida). U hosila ustun, ya'ni
           texnik jihatdan ham mumkin emas; lekin qoidaning mazmuni
           kengroq — o'sha paytda qilingan hisob retroaktiv bekor
           qilinmaydi.

        ⚠ `object_deleted_at` MAJBURIY va uni sxema ham talab qiladi
          (`purged_has_deletion_time` CHECK). Sanasiz `purged` qator
          «kadr mavjud edi, arxivdan chiqarildi» da'vosini SANASIZ
          qoldirardi va operator uni «yo'qolgan kadr» dan ajrata olmasdi.

        ⚠ VAQT DB SOATIDAN (`now()`): retention so'rovlari ham AYNAN o'sha
          soatga qarab qaror qiladi.

        Returns:
            `full` yoki `compressed` holatdagi qator topilib o'tgan bo'lsa
            `True`. Ikkinchi chaqiruv `False` beradi — `purged` qatlami
            `PURGEABLE_TIERS` da yo'q, ya'ni o'chirish vaqti QAYTA
            yozilmaydi.
        """
        result = await self.session.execute(
            update(Snapshot)
            .where(
                Snapshot.market_id == self.market_id,
                Snapshot.id == snapshot_id,
                Snapshot.storage_tier.in_(PURGEABLE_TIERS),
            )
            .values(storage_tier=SnapshotTier.PURGED.value, object_deleted_at=func.now())
            .returning(Snapshot.id)
        )
        return result.scalar_one_or_none() is not None


def _as_numeric(value: float | None) -> Decimal | None:
    """`float` -> `Decimal` — `Numeric(6, 2)` ustunlari uchun.

    ⚠ `Decimal(str(value))` , `Decimal(value)` EMAS: ikkinchisi ikkilik
      float artefaktini olib kiradi (`Decimal(0.1)` ->
      `0.1000000000000000055511151231257827021181583404541015625`) va u
      `Numeric(6, 2)` ga sig'may xato berardi. `str()` orqali o'tish esa
      `quality.py` qaytargan sonni AYNAN o'nlik ko'rinishida beradi.

    `None` o'tkaziladi: `quality_saturation` NULLABLE («o'lchanmadi»).
    """
    return None if value is None else Decimal(str(value))
