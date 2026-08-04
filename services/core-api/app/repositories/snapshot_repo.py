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

from sbozor_core.enums import SnapshotQuality, SnapshotTier
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
    """O'lchovsiz kadr `corrupt` DAN BOSHQA verdikt bilan yozilmoqchi bo'ldi.

    =========================================================================
    ⛔ `04-05` OCHIQ QOLDIRGAN ZIDDIYAT SHU YERDA YOPILDI (qarorning egasi
       `04-07`, migratsiya `0016`).

    Ziddiyatning eski shakli: `04-03` ustunlarni `NOT NULL` qilgan,
    `04-04` esa `corrupt` kadr uchun o'lchovlarni `None` qaytaradi, ya'ni
    UI-SPEC §6.4 ning C4 hujayrasi (`succeeded` + `corrupt`) YOZIB
    BO'LMAYDIGAN bo'lib qolgan edi. Ikki taklif qilingan yechim —
    «(a) `corrupt` umuman yozilmaydi» va «(b) ustunlar NULLABLE» — bir
    vaqtda to'g'ri bo'la olmaydi deb baholangan edi.

    **O'LCHOV KO'RSATDIKI, SAVOL NOTO'G'RI QO'YILGAN EDI: ikkala yo'l ham
    kerak, chunki ular IKKI XIL nosozlikni ifodalaydi va ular IKKI XIL
    QATLAMDA hal bo'ladi.**

        javob UMUMAN kadr emas (HTML sahifa, bo'sh tana, JPEG bo'lmagan
        bayt) -> `frame_source` ning magic-bayt darvozasi uni sifat
        tahliliga QO'YMAYDI -> `capture_invalid_response`, qator `failed`,
        `snapshots` qatori YO'Q                                  <- (a)

        javob KADR, lekin YAROQSIZ (kesilgan JPEG, dekod xatosi)
        -> `quality.analyze()` uni `corrupt` deydi va o'lchovlar `None`
        -> qator `succeeded`, `snapshots` qatori BOR, `is_billable=false`,
           C4 hujayrasi CHIZILADI                                <- (b)

    Ya'ni `capture_invalid_response` HAM ishlatiladi, C4 hujayrasi HAM
    mavjud bo'ladi.
    =========================================================================

    ⚠ DARVOZA OLIB TASHLANMADI, TORAYTIRILDI. `corrupt` dan boshqa verdikt
      uchun o'lchov MAJBURIY bo'lib qoladi: `ok` kadrni o'lchovsiz yozish
      D-15 ning butun mexanizmini (chegaralarni haqiqiy taqsimotdan
      chiqarish) jimgina buzardi va nosozlik faqat Phase 0 da, chegara
      sozlanayotganda ko'rinardi.

    ⚠ SENTINEL NOL EMAS: `0` bazada «o'lchandi va nol chiqdi» degan
      MA'NOGA ega bo'lardi va `percentile_cont` ni pastga tortardi.
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
            SnapshotMeasurementMissingError: o'lchov `None`, LEKIN verdikt
                `corrupt` EMAS. `corrupt` kadr uchun `None` — qonuniy
                holat (`0016` migratsiyasi); o'sha sinf docstringiga
                qarang.
            IntegrityError: shu `capture_run_id` uchun ikkinchi kadr
                (`uq_snapshots_market_id_capture_run_id`, `23505`) yoki
                takroriy `object_key`. Chaqiruvchi uni 409 ga aylantiradi;
                ikkinchi kadr «qaysi biri dalil?» savolini javobsiz
                qoldirardi va 5-faza tasodifiy birini tanlardi.
        """
        measured = quality_mean is not None and quality_stddev is not None
        if not measured and quality_verdict != SnapshotQuality.CORRUPT.value:
            raise SnapshotMeasurementMissingError(
                f"quality_verdict={quality_verdict!r} uchun o'lchovlar yo'q "
                f"(mean={quality_mean}, stddev={quality_stddev}). O'lchovsiz "
                f"yozish faqat {SnapshotQuality.CORRUPT.value!r} verdiktida "
                "ruxsat etiladi (`0016` migratsiyasi) — qolgan verdiktlarda "
                "D-15 ning chegara chiqarish yo'li o'lchovga TAYANADI."
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
