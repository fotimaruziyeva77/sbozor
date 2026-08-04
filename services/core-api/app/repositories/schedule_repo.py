"""Mavsumiy kadr-olish profillari — davr bo'lish va qoplanmagan kunlar (CAM-04).

=============================================================================
1-QAROR: ORALIQ SAQLANMAYDI, TEKIS VAQTLAR RO'YXATI SAQLANADI.

«06:00–08:00 har 30 daqiqada» — UI ning GENERATOR TUGMASI
(`04-UI-SPEC.md` §4.6), baza esa faqat beshta qatorni ko'radi. Ikkala
shaklni ham saqlash IKKI KOD YO'LINI tug'dirardi: materializatsiya
oraliqni kengaytirishi kerak bo'lardi, hisobot esa ikkala shakl bilan ham
ishlashi kerak bo'lardi — va ular bir kun ajralib ketardi
(`04-RESEARCH.md` §A.1).
=============================================================================

=============================================================================
2-QARO R: BO'SHLIQ ATAYIN MUMKIN VA U XATO EMAS — LEKIN U KO'RINISHI SHART.

Ikki profil orasidagi qoplanmagan kunda umuman slot yo'q, ya'ni kadr
olinmaydi. Mavsumiy yopiladigan bozor uchun bu TO'G'RI xulq va shuning
uchun uzluksizlik MAJBURLANMAYDI (`sbozor_core/periods.py` dagi D-11 ning
aynan bir xil qarori).

Lekin ko'rinmasa bu JIM MA'LUMOT YO'QOTISH bo'lardi: admin bir oydan
keyin hisobotdagi bo'shliqni ko'rib «tizim buzilibdi» deb o'ylardi.
Shuning uchun `uncovered_days()` — bu qatlamning BIRINCHI DARAJALI
metodi, qo'shimcha emas, va `today_and_tomorrow()` uni HAR DOIM qaytaradi.
=============================================================================

=============================================================================
3-QAROR: KESISHISHNI ILOVA TEKSHIRMAYDI.

Yagona qo'riqchi — `ex_snapshot_schedules_no_overlap` (`EXCLUDE USING
gist`, SQLSTATE `23P01`). «Avval kesishuvni tekshir, keyin yoz» ikki
parallel so'rovda IKKALASINI ham o'tkazib yuborardi va bir kunga ikki xil
slot to'plami paydo bo'lardi — o'shanda materializatsiya qaysi biriga
tayanishni TASODIFGA qoldirardi va SC#1 («ertasi kuni aynan o'sha
slotlarda») tekshirib bo'lmaydigan holga kelardi (T-04-19).

Bu sinfning ishi — konstraytni takrorlash emas, uning xatosini TANILGAN
xatoga aylantirish. `ScheduleOverlapError` -> 409; xom `IntegrityError`
esa 500 bo'lib chiqardi (`vendor_repo.AssignmentRepository` bilan bir xil
chegara, faqat u aylantirishni chaqiruvchiga qoldiradi — bu yerda esa
`create_seasonal()` bir necha operatorni bajaradi va qaysi biri yiqilgani
faqat shu sinfga ma'lum).

⚠ `IntegrityError` DAN KEYIN TRANZAKSIYA O'LGAN bo'ladi. Chaqiruvchi uni
  ROLLBACK qilishi shart — bu istisnoning tipiga bog'liq emas va har
  qanday `IntegrityError` yo'lida ham shunday.
=============================================================================

DAVR CHEGARASI — `sbozor_core.periods.assignment_period()` orqali va
BOSHQA HECH QAYERDAN. Xom diapazon konstruktori yozilmaydi (Pitfall 10):
`[)` va `[]` bir xil darajada yozish mumkin bo'lgan shakl va ikkalasi
bitta kod bazasida yashasa mavsum ALMASHINUV KUNIDA ikkita profil bir
vaqtda amal qilardi.

⚠ FUNKSIYA NOMI «assignment» DEB BOSHLANADI VA U SHU YERDA HAM
  ISHLATILADI. `sbozor_core/periods.py` ning modul docstringi uni
  loyihadagi YAGONA `[)` manbai deb e'lon qiladi, ya'ni nom domenga emas,
  KONVENSIYAGA tegishli. Unga juft yasash (`schedule_period()`) ikkinchi
  ta'rif nuqtasini tug'dirardi va aynan o'sha docstring buni taqiqlaydi.

⛔ O'CHIRISH BU YERDA RUXSAT ETILADI VA BU FAZADAGI YAGONA ISTISNO.
  `capture_repo` va `snapshot_repo` hech nimani o'chirmaydi (dalil
  zanjiri). Bu yerdagi farq TUZILMAVIY: hali BOSHLANMAGAN profil birorta
  `capture_runs` qatorini tug'dirmagan, ya'ni o'chiriladigan DALIL yo'q.
  `delete_future()` esa xato bilan kiritilgan mavsumni tuzatishning
  YAGONA yo'li (`04-UI-SPEC.md` DL-4). Amal baribir izsiz emas: ikkala
  jadval ham `AUDITED_TABLES` da va o'chirish audit jurnaliga tushadi —
  «slotni olib tashlash nazoratni JIMGINA o'chirishning eng arzon yo'li»
  degan sabab bilan (`models/snapshot.py::SnapshotSchedule`).

TENANT FILTRI IKKI QATLAM: RLS policy'si himoya to'ri, `market_id`
predikati esa aniq filtr. Xom SQL'da u QO'LDA, ko'rinadigan joyda turadi.

XATO SINFLARI VA ULARNING HTTP JAVOBLARI — CHAQIRUVCHI UCHUN KONTRAKT
(`tariff_repo` ning `ValidFromNotAllowedError` naqshi):

    ScheduleStartsTooSoonError   -> 422  (D-05: eng erta — ertaga)
    ScheduleSlotsInvalidError    -> 422  (son, dublikat, bo'sh ro'yxat)
    ScheduleNotEditableError     -> 403  (o'tmish yoki boshlangan profil)
    ScheduleOverlapError         -> 409  (`EXCLUDE`, `23P01`)

To'rttasi ham `ValueError` dan meros oladi, ya'ni umumiy `except
ValueError` ularning HAMMASINI tutadi — lekin javob kodlari FARQLI va
shuning uchun ular bitta sinfga yig'ilmagan.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time
from typing import TYPE_CHECKING
from uuid import UUID

from sbozor_core.models import SnapshotSchedule, SnapshotScheduleSlot
from sbozor_core.periods import assignment_period
from sbozor_core.tenancy import TenantScopedRepository
from sqlalchemy import Date, Integer, bindparam, delete, func, insert, select, text, update
from sqlalchemy.dialects.postgresql import UUID as PgUuid
from sqlalchemy.exc import IntegrityError

from app.repositories.stall_repo import sqlstate_of

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

__all__ = [
    "EXCLUSION_VIOLATION",
    "DayPlan",
    "ScheduleNotEditableError",
    "ScheduleOverlapError",
    "ScheduleProfile",
    "ScheduleRepository",
    "ScheduleSlotsInvalidError",
    "ScheduleStartsTooSoonError",
    "ScheduleView",
]

EXCLUSION_VIOLATION = "23P01"
"""`EXCLUDE` konstraytining SQLSTATE kodi.

`app/api/v1/assignments.py:154` da AYNAN shu literal bor va bu nusxa
ATAYIN: ikkala modul ham o'z chegarasini o'zi hujjatlaydi va ular BOSHQA
konstraytlar haqida gapiradi (`stall_assignments` va `snapshot_schedules`).
Umumiy konstantaga chiqarish ikkalasini bir-biriga bog'lab qo'yardi.
"""

_PAST = "past"
_ACTIVE = "active"
_FUTURE = "future"
"""Profil rejimlari — `04-UI-SPEC.md` §4.5 ning uch qatori.

Ular DB kontenti EMAS, hisoblanadigan qiymat: profilning o'zi faqat davrni
biladi, «o'tmishmi yoki kelajakmi» esa BUGUNGA nisbatan aniqlanadi.
Ustunga yozib qo'yish har kuni yarim tunda migratsiya talab qilardi.
"""


class ScheduleStartsTooSoonError(ValueError):
    """Mavsumiy profil BUGUN yoki undan oldin boshlanmoqchi (D-05) -> 422.

    Bugundan boshlanadigan profil bugungi rejani IKKI XIL holatda
    qoldirardi: ertalabki slotlar eski jadvaldan materializatsiya
    qilingan, kechkilari esa yangisidan — «shu kunda qaysi jadval amal
    qildi?» savoli javobsiz qolardi va o'sha kunning hisoboti hech qaysi
    profil bilan tushuntirilmasdi.
    """


class ScheduleSlotsInvalidError(ValueError):
    """Vaqtlar to'plami yaroqsiz: bo'sh, dublikatli yoki chegaradan oshiq -> 422.

    ⚠ CHEGARA SERVERDA MAJBURLANADI (`04-UI-SPEC.md` §4.6 `[TALAB]`).
      Klientdagi `MAX_TIMES_PER_DAY` — QULAYLIK: u foydalanuvchini
      chegaraga YETGUNICHA ogohlantiradi, lekin DevTools bilan olib
      tashlanadi. Arifmetika: 12 x 25 kamera = 300 kadr/kun ≈ 6,5 GB/yil;
      chegarasiz «06:00–20:00 har 5 daqiqada» = 169 vaqt = 4 225 kadr/kun
      va Contabo diski bir necha oyda to'lardi.

    ⚠ BO'SH RO'YXAT HAM RAD ETILADI: nol vaqt — kadr olinmaydigan bozor.
      Uni jadval orqali yasash mumkin bo'lsa nazoratni o'chirishning eng
      jim yo'li paydo bo'lardi (profil bor, jurnal bo'sh).
    """


class ScheduleNotEditableError(ValueError):
    """Profil o'tmishda yoki allaqachon boshlangan -> 403.

    O'tmishdagi profil o'tmishdagi kadrlarni TUSHUNTIRADI: «o'sha kuni
    nega faqat 5 kadr bor?» savolining javobi aynan o'sha profil.
    Tahrirlash tarixni yolg'onga aylantirardi va buni hech kim sezmasdi —
    kadrlar joyida qolardi, izoh esa boshqa bo'lardi.

    403 (404 EMAS): qator MAVJUD va uni chaqiruvchi ko'ra oladi; rad
    etilayotgani AMAL. Cross-tenant holati esa BUTUNLAY BOSHQA yo'ldan
    ketadi — u `None`/`False` bo'lib qaytadi va 404 ga aylanadi
    (`tariff_repo.get` bilan bir xil qaror va bir xil sabab).
    """


class ScheduleOverlapError(ValueError):
    """Yozilayotgan davr mavjud profil bilan kesishadi (`23P01`) -> 409.

    Modul docstringidagi 3-qarorga qarang: bu shart ILOVADA
    TEKSHIRILMAYDI, konstrayt bajaradi. Bu sinf faqat uning xatosini
    tanilgan qilib beradi.
    """


@dataclass(frozen=True, slots=True)
class ScheduleProfile:
    """Bitta profil — `04-UI-SPEC.md` §4.3 ning `profile` obyekti.

    `ends_on` `None` — ochiq oxirli («hozircha amaldagi profil»).
    `mode` HISOBLANADI (yuqoridagi konstantalar izohiga qarang).
    """

    id: UUID
    name: str
    starts_on: date
    ends_on: date | None
    mode: str


@dataclass(frozen=True, slots=True)
class DayPlan:
    """Bitta kunning vaqtlari — `date` va `times` BIRGA.

    Sana ATAYIN shu obyektning ichida: `times` yolg'iz qaytarilsa UI uning
    QAYSI kunga tegishli ekanini o'zi hisoblab olardi va yarim tunda
    server bilan bir kun farq qilardi.
    """

    date: date
    times: tuple[time, ...]


@dataclass(frozen=True, slots=True)
class ScheduleView:
    """Jadval sahifasining butun holati — BITTA so'rovdan (`04-UI-SPEC.md` §4.3).

    ⛔ `today` VA `tomorrow` BITTA LAHZADAN. Ikki so'rovga bo'linsa ular
       TURLI lahzada olinardi va yarim tun atrofida ikkalasi bir kunni
       ko'rsatib qolardi — ya'ni D-05 ning butun ko'rsatkichi («bugun 7
       slot · ertaga 5 slot») aynan eng muhim daqiqada yolg'on bo'lardi.

    `profile` `None` bo'lishi mumkin: bozorda birorta profil bo'lmasa.
    Bugun QOPLANMAGAN bo'lsa esa `profile` eng yaqin profilni beradi va
    `mode` uning qaysi tomonda ekanini aytadi — shunda UI «keyingi jadval
    {sana} da boshlanadi» deya oladi.

    `differs` PROFIL bo'yicha hisoblanadi, vaqtlar ro'yxati bo'yicha emas:
    ikki profilning vaqtlari tasodifan bir xil bo'lishi mumkin, lekin UI
    ogohlantirishi «jadval o'zgaradi» haqida.
    """

    profile: ScheduleProfile | None
    today: DayPlan
    tomorrow: DayPlan
    differs: bool
    capture_on_closed_days: bool
    uncovered_days: int
    uncovered_horizon_days: int


# ===========================================================================
# XOM SQL — «bitta so'rov» talabi ORM'da ifodalanmaydi
# ===========================================================================

_TODAY_AND_TOMORROW = text(
    """
    WITH days AS (
        SELECT (now() AT TIME ZONE m.timezone)::date        AS today,
               (now() AT TIME ZONE m.timezone)::date + 1    AS tomorrow
          FROM markets m
         WHERE m.id = :market_id
    ),
    today_schedule AS (
        SELECT s.id
          FROM snapshot_schedules s
         CROSS JOIN days d
         WHERE s.market_id = :market_id
           AND s.period @> d.today
    ),
    tomorrow_schedule AS (
        SELECT s.id
          FROM snapshot_schedules s
         CROSS JOIN days d
         WHERE s.market_id = :market_id
           AND s.period @> d.tomorrow
    ),
    nearest AS (
        SELECT s.id,
               s.name,
               lower(s.period) AS starts_on,
               upper(s.period) AS ends_on,
               CASE WHEN s.period @> d.today       THEN 'active'
                    WHEN lower(s.period) > d.today THEN 'future'
                    ELSE 'past' END AS mode
          FROM snapshot_schedules s
         CROSS JOIN days d
         WHERE s.market_id = :market_id
         ORDER BY CASE WHEN s.period @> d.today       THEN 0
                       WHEN lower(s.period) > d.today THEN 1
                       ELSE 2 END,
                  abs(lower(s.period) - d.today)
         LIMIT 1
    ),
    today_times AS (
        SELECT coalesce(array_agg(sl.slot_time ORDER BY sl.slot_time), ARRAY[]::time[]) AS times
          FROM snapshot_schedule_slots sl
         WHERE sl.market_id = :market_id
           AND sl.schedule_id = (SELECT id FROM today_schedule)
    ),
    tomorrow_times AS (
        SELECT coalesce(array_agg(sl.slot_time ORDER BY sl.slot_time), ARRAY[]::time[]) AS times
          FROM snapshot_schedule_slots sl
         WHERE sl.market_id = :market_id
           AND sl.schedule_id = (SELECT id FROM tomorrow_schedule)
    ),
    gaps AS (
        SELECT count(*) AS uncovered
          FROM days d
         CROSS JOIN generate_series(d.today, d.today + (:horizon_days - 1), '1 day') AS g(day)
         WHERE NOT EXISTS (
             SELECT 1
               FROM snapshot_schedules s
              WHERE s.market_id = :market_id
                AND s.period @> g.day::date
         )
    )
    SELECT d.today,
           d.tomorrow,
           n.id            AS profile_id,
           n.name          AS profile_name,
           n.starts_on,
           n.ends_on,
           n.mode          AS profile_mode,
           tt.times        AS today_times,
           mt.times        AS tomorrow_times,
           (SELECT id FROM tomorrow_schedule)
               IS DISTINCT FROM (SELECT id FROM today_schedule) AS differs,
           coalesce(p.capture_on_closed_days, true) AS capture_on_closed_days,
           g.uncovered
      FROM days d
      LEFT JOIN nearest n ON true
      CROSS JOIN today_times tt
      CROSS JOIN tomorrow_times mt
      CROSS JOIN gaps g
      LEFT JOIN market_profile p ON p.market_id = :market_id
    """
).bindparams(
    bindparam("market_id", type_=PgUuid(as_uuid=True)),
    bindparam("horizon_days", type_=Integer()),
)
"""Jadval sahifasining butun holati — AYNAN BITTA `SELECT`.

⛔ BITTA SO'ROV — MEXANIK TALAB, uslub emas. `today` va `tomorrow` bir
   `now()` dan chiqadi, ya'ni ular hech qachon bir kunni ko'rsata olmaydi.
   Ikki so'rovga bo'lingan variant yarim tun atrofida AYNAN shunday qilardi
   va D-05 ning ko'rsatkichi eng muhim daqiqada yolg'on bo'lardi. Talab
   `tests/integration/test_schedule_repo.py` da SQL operatorlarini SANAB
   qulflangan.

⚠ «BUGUN» BOZORNING O'Z MINTAQASIDAN (`m.timezone`), ilova soatidan EMAS.
  Yozish yo'llari (`create_seasonal`, `update_slots`, `delete_future`) esa
  `today` ni ARGUMENT sifatida oladi va bu ZIDDIYAT EMAS: bitta HTTP
  so'rovi ichidagi bir necha operator AYNAN bir xil biznes-kunga tayanishi
  kerak (`tariff_repo.tariff_window(today)` bilan bir xil qaror). O'qish
  yo'lida esa aksincha — atomiklik MUHIM va argument uni buzardi.

⚠ `nearest` — bugunni QOPLAYDIGAN profil BO'LMASA ham javob beradi.
  Tartiblash uch pog'onali: (1) bugunni qoplaydigani, (2) eng yaqin
  KELAJAKDAGI, (3) eng yaqin O'TMISHDAGI. Uchinchi kalit
  `abs(lower(period) - today)` — u ikkala yo'nalish uchun ham «eng
  yaqini» ni beradi, ya'ni ikkita alohida `ORDER BY` shoxi kerak emas.
  `NULL` qaytarish (profil bor-u, ko'rsatilmaydi) UI'ni «jadval yo'q»
  holatiga tushirardi va admin mavjud mavsumni umuman ko'rmasdi.

⚠ `array_agg` + `coalesce(..., ARRAY[]::time[])`: qoplanmagan kunda
  ro'yxat BO'SH bo'ladi, `NULL` emas. `NULL` chaqiruvchini har joyda
  `or []` yozishga majburlardi va ulardan bittasi uni unutardi.

⚠ `generate_series(today, today + horizon - 1)` — AYNAN `horizon_days` ta
  kun. `+ horizon` yozilsa oyna bir kun uzun bo'lardi va UI «keyingi 90
  kun» deb turib 91 kunni sanardi.

⚠ `IS DISTINCT FROM` — oddiy `<>` EMAS: bugun qoplanmagan (`NULL`) va
  ertaga qoplangan holat `<>` bilan `NULL` berardi va `differs` jimgina
  `false` bo'lib qolardi, ya'ni jadval ertadan boshlanishi haqidagi
  ogohlantirish AYNAN eng kerakli holatda ko'rinmasdi.
"""

_UNCOVERED_DAYS = text(
    """
    WITH days AS (
        SELECT (now() AT TIME ZONE m.timezone)::date AS today
          FROM markets m
         WHERE m.id = :market_id
    )
    SELECT count(*)
      FROM days d
     CROSS JOIN generate_series(d.today, d.today + (:horizon_days - 1), '1 day') AS g(day)
     WHERE NOT EXISTS (
         SELECT 1
           FROM snapshot_schedules s
          WHERE s.market_id = :market_id
            AND s.period @> g.day::date
     )
    """
).bindparams(
    bindparam("market_id", type_=PgUuid(as_uuid=True)),
    bindparam("horizon_days", type_=Integer()),
)
"""Qoplanmagan kunlar SQL'DA sanaladi, Python'da EMAS.

90 kunni tarmoqdan olib kelib sanash bir xil javobni ancha qimmatga
berardi va har bir chaqiruvchi «qaysi kunlar?» degan savolga o'z javobini
yozardi. `today_and_tomorrow()` dagi `gaps` CTE'si bilan AYNAN bir xil
ifoda — nusxa ATAYIN, chunki u yerda so'rovni BITTA qilib qoldirish
talabi bor va bu metodni chaqirish ikkinchi so'rov bo'lardi.
"""

_PROFILE_FOR_DAY = text(
    """
    SELECT s.id,
           s.name,
           lower(s.period) AS starts_on,
           upper(s.period) AS ends_on
      FROM snapshot_schedules s
     WHERE s.market_id = :market_id
       AND s.period @> :day
    """
).bindparams(
    bindparam("market_id", type_=PgUuid(as_uuid=True)),
    bindparam("day", type_=Date()),
)
"""Berilgan kunni QOPLAYDIGAN profil — `EXCLUDE` tufayli KO'PI BILAN bitta.

`scalar_one_or_none()` shuning uchun to'g'ri va u konstrayt buzilganda
JIMGINA birinchi qatorni olib qo'ymaydi (`nvr_repo.active_run_id` bilan
bir xil qaror).
"""

_COPY_SLOTS = text(
    """
    INSERT INTO snapshot_schedule_slots (market_id, schedule_id, slot_time)
    SELECT :market_id, :target_id, sl.slot_time
      FROM snapshot_schedule_slots sl
     WHERE sl.market_id = :market_id
       AND sl.schedule_id = :source_id
    """
).bindparams(
    bindparam("market_id", type_=PgUuid(as_uuid=True)),
    bindparam("target_id", type_=PgUuid(as_uuid=True)),
    bindparam("source_id", type_=PgUuid(as_uuid=True)),
)
"""Tiklangan NUSXAGA vaqtlarni ko'chiradi — BITTA operatorda.

⚠ VAQTLARNI KO'CHIRISH MAJBURIY. Nusxa bo'sh qolsa u qoplanmagan kundan
  FARQ QILMASDI: profil bor, slot yo'q, kadr olinmaydi — va admin uni
  jadvalda ko'rib «hammasi joyida» deb o'ylardi. Bu bo'shliqdan ham
  yomonroq, chunki `uncovered_days()` uni sanamasdi ham.
"""


class ScheduleRepository(TenantScopedRepository):
    """`snapshot_schedules` + `snapshot_schedule_slots` ustidagi butun yuza."""

    # ------------------------------------------------------------------
    # O'qish
    # ------------------------------------------------------------------

    async def today_and_tomorrow(self, *, horizon_days: int) -> ScheduleView:
        """Jadval sahifasining butun holati — BITTA so'rovda (`04-UI-SPEC.md` §4.3).

        Args:
            horizon_days: qoplanish ufqi (UI «keyingi {n} kun» deb
                yozadi). `Settings` dan emas, ARGUMENTDAN keladi —
                repozitoriy sozlamalarni bilmaydi (04-04 da o'rnatilgan
                sof-modul chegarasi bilan bir xil qoida).
        """
        result = await self.session.execute(
            _TODAY_AND_TOMORROW,
            {"market_id": self.market_id, "horizon_days": horizon_days},
        )
        row = result.one_or_none()
        if row is None:
            # Bozor qatori ko'rinmadi (kontekst yo'q yoki begona bozor).
            # ⚠ Istisno EMAS: RLS ostida bu NORMAL javob va chaqiruvchi
            #   uni 404 ga aylantiradi. Istisno 500 bo'lib chiqardi.
            empty = DayPlan(date=date.min, times=())
            return ScheduleView(
                profile=None,
                today=empty,
                tomorrow=empty,
                differs=False,
                capture_on_closed_days=True,
                uncovered_days=0,
                uncovered_horizon_days=horizon_days,
            )

        profile = (
            None
            if row.profile_id is None
            else ScheduleProfile(
                id=row.profile_id,
                name=row.profile_name,
                starts_on=row.starts_on,
                ends_on=row.ends_on,
                mode=row.profile_mode,
            )
        )
        return ScheduleView(
            profile=profile,
            today=DayPlan(date=row.today, times=tuple(row.today_times)),
            tomorrow=DayPlan(date=row.tomorrow, times=tuple(row.tomorrow_times)),
            differs=bool(row.differs),
            capture_on_closed_days=bool(row.capture_on_closed_days),
            uncovered_days=int(row.uncovered),
            uncovered_horizon_days=horizon_days,
        )

    async def active_profile(self, on: date) -> ScheduleProfile | None:
        """Berilgan kunni QOPLAYDIGAN profil yoki `None` (bo'shliq).

        `None` — XATO EMAS (modul docstringidagi 2-qaror). Chaqiruvchi
        uni «bu kunga kadr olinmaydi» deb talqin qiladi va
        `uncovered_days()` uni SANAYDI.
        """
        result = await self.session.execute(
            _PROFILE_FOR_DAY, {"market_id": self.market_id, "day": on}
        )
        row = result.one_or_none()
        if row is None:
            return None
        return ScheduleProfile(
            id=row.id,
            name=row.name,
            starts_on=row.starts_on,
            ends_on=row.ends_on,
            mode=_mode_of(row.starts_on, row.ends_on, on),
        )

    async def slots_for(self, day: date) -> list[time]:
        """Shu kunga amal qiladigan vaqtlar (o'sish tartibida).

        ⚠ QOPLANMAGAN KUN uchun BO'SH ro'yxat — istisno EMAS. Istisno
          bo'lsa `ensure_plan()` ni chaqiradigan tik BUTUN BOZOR uchun
          yiqilardi, holbuki bo'shliq xato emas.
        """
        result = await self.session.execute(
            select(SnapshotScheduleSlot.slot_time)
            .join(
                SnapshotSchedule,
                SnapshotSchedule.id == SnapshotScheduleSlot.schedule_id,
            )
            .where(
                SnapshotScheduleSlot.market_id == self.market_id,
                SnapshotSchedule.market_id == self.market_id,
                SnapshotSchedule.period.contains(day),
            )
            .order_by(SnapshotScheduleSlot.slot_time)
        )
        return list(result.scalars().all())

    async def uncovered_days(self, *, horizon_days: int) -> int:
        """Ufq ichidagi QOPLANMAGAN kunlar soni (modul docstringidagi 2-qaror)."""
        result = await self.session.execute(
            _UNCOVERED_DAYS, {"market_id": self.market_id, "horizon_days": horizon_days}
        )
        return int(result.scalar_one())

    # ------------------------------------------------------------------
    # Yozish — davr BO'LINADI
    # ------------------------------------------------------------------

    async def create_seasonal(
        self,
        *,
        name: str,
        starts_on: date,
        ends_on: date | None,
        times: Iterable[time],
        today: date,
        max_times_per_day: int,
    ) -> UUID:
        """Mavsumiy profil qo'shadi — MAVJUD davrni BO'LIB (`04-RESEARCH.md` §A.1).

        Uch qadam va uchalasi ham BITTA tranzaksiyada:

          1. `starts_on` ni qoplaydigan profil `[boshlanish, starts_on)`
             ga QISQARTIRILADI;
          2. `ends_on` berilgan VA o'sha profil `ends_on` dan keyin ham
             davom etgan bo'lsa — u `[ends_on, eski_oxir)` da NUSXA
             sifatida TIKLANADI (vaqtlari bilan birga);
          3. Yangi profil `[starts_on, ends_on)` yoziladi.

        Natija (`04-RESEARCH.md` §A.1 misoli):

            [08-15, 11-01)  "Standart"
            [11-01, 03-01)  "Qishki"
            [03-01, ∞)      "Standart"   (nusxa)

        ⚠ NUSXANING NOMI ASL NOM BILAN BIR XIL. UI «Keyin «{nom}»
          jadvali qaytadi» jumlasini AYNAN shundan chizadi
          (`04-UI-SPEC.md` §4.7). «Standart (nusxa)» kabi nom o'sha
          jumlani yolg'on qilardi va admin uchun ikkinchi, tushunarsiz
          profil paydo bo'lardi.

        ⚠ `starts_on` DA BOSHLANADIGAN PROFIL BO'LSA amal RAD ETILADI:
          uni qisqartirish BO'SH davr (`[a, a)`) berardi va
          `period_not_empty` CHECK'i yiqilardi. Bunday holat mavjud
          kelajakdagi profilni JIMGINA yo'q qilishni anglatardi, shuning
          uchun javob — tanilgan xato, avtomatik almashtirish emas.

        Raises:
            ScheduleStartsTooSoonError: `starts_on <= today` (D-05).
            ScheduleSlotsInvalidError: vaqtlar to'plami yaroqsiz.
            ScheduleOverlapError: davr mavjud profil bilan kesishadi.
            ValueError: `ends_on <= starts_on` (`assignment_period()` ning
                O'Z darvozasi).
        """
        slots = _normalize(times, max_times_per_day)
        if starts_on <= today:
            raise ScheduleStartsTooSoonError(
                f"mavsumiy profil eng erta ERTAGA boshlanishi mumkin "
                f"(berilgan: {starts_on.isoformat()}, bugun: {today.isoformat()}). "
                "D-05: bugungi reja allaqachon materializatsiya qilingan."
            )
        period = assignment_period(starts_on, ends_on)

        try:
            covering = await self.active_profile(starts_on)
            if covering is not None:
                if covering.starts_on >= starts_on:
                    raise ScheduleOverlapError(
                        f"{starts_on.isoformat()} kunida boshlanadigan profil "
                        f"allaqachon bor ({covering.name!r}). Uni tahrirlang yoki "
                        "o'chiring — avtomatik almashtirish qilinmaydi."
                    )
                await self._set_period(covering.id, covering.starts_on, starts_on)
                if ends_on is not None and (covering.ends_on is None or covering.ends_on > ends_on):
                    await self._restore_copy(covering, resumes_on=ends_on)

            schedule_id = await self._insert_profile(name, period)
            await self._insert_slots(schedule_id, slots)
        except IntegrityError as exc:
            if sqlstate_of(exc) == EXCLUSION_VIOLATION:
                raise ScheduleOverlapError(
                    f"davr {starts_on.isoformat()}..{ends_on.isoformat() if ends_on else '∞'} "
                    "mavjud profil bilan kesishadi"
                ) from exc
            raise
        return schedule_id

    async def update_slots(
        self,
        schedule_id: UUID,
        times: Iterable[time],
        *,
        today: date,
        max_times_per_day: int,
    ) -> bool:
        """Profilning vaqtlarini ALMASHTIRADI (`04-UI-SPEC.md` §4.5).

        ⚠ BUGUNGI REJAGA TA'SIR QILMAYDI (D-05) va bu kafolat SHU YERDA
          EMAS: bugungi `capture_runs` qatorlari allaqachon
          materializatsiya qilingan va `capture_repo.ensure_plan()` ning
          slot-o'lchovidagi muzlatishi ularga yangi vaqt qo'shmaydi. UI
          DL-1 da buni doimiy izoh bilan aytadi.

        ⚠ ESKI VAQTLAR O'CHIRILADI VA YANGILARI YOZILADI. Bu modul
          docstringidagi o'chirish istisnosining ikkinchi yuzi: slot —
          profilning tarkibiy qismi, mustaqil hayot sikliga ega emas.
          O'zgarish audit jurnaliga tushadi (jadval `AUDITED_TABLES` da),
          ya'ni «nazoratni jimgina kamaytirish» yo'li yopiq.

        Returns:
            Profil topilib yangilangan bo'lsa `True`. `False` — profil
            yo'q yoki BEGONA bozorniki (RLS uni ko'rsatmadi) -> 404.

        Raises:
            ScheduleSlotsInvalidError: vaqtlar to'plami yaroqsiz.
            ScheduleNotEditableError: profil O'TMISHDA -> 403.
        """
        slots = _normalize(times, max_times_per_day)
        profile = await self._profile_by_id(schedule_id)
        if profile is None:
            return False
        if _mode_of(profile.starts_on, profile.ends_on, today) == _PAST:
            raise ScheduleNotEditableError(
                f"{profile.name!r} profili o'tmishda "
                f"({profile.starts_on.isoformat()}..{profile.ends_on}) va u o'sha "
                "kunlardagi kadrlarni tushuntiradi — tahrirlash mumkin emas."
            )

        await self.session.execute(
            delete(SnapshotScheduleSlot).where(
                SnapshotScheduleSlot.market_id == self.market_id,
                SnapshotScheduleSlot.schedule_id == schedule_id,
            )
        )
        await self._insert_slots(schedule_id, slots)
        return True

    async def delete_future(self, schedule_id: UUID, *, today: date) -> bool:
        """HALI BOSHLANMAGAN profilni o'chiradi (`04-UI-SPEC.md` DL-4).

        ⛔ FAQAT `starts_on > today`. Modul docstringining oxirgi bandiga
           qarang: bunday profil birorta `capture_runs` qatorini
           tug'dirmagan, ya'ni o'chiriladigan DALIL yo'q. Boshlangan
           profilni o'chirish esa o'tmishdagi kadrlarning yagona izohini
           yo'q qilardi.

        Slotlar `ON DELETE CASCADE` bilan ketadi (`models/snapshot.py`).
        O'chgan kunlar QOPLANMAGAN bo'lib qoladi va `uncovered_days()`
        ularni ko'rsatadi — jim ma'lumot yo'qotish emas.

        Returns:
            O'chirilgan bo'lsa `True`; profil topilmasa yoki begona
            bozorniki bo'lsa `False` -> 404.

        Raises:
            ScheduleNotEditableError: profil allaqachon boshlangan -> 403.
        """
        profile = await self._profile_by_id(schedule_id)
        if profile is None:
            return False
        if profile.starts_on <= today:
            raise ScheduleNotEditableError(
                f"{profile.name!r} profili {profile.starts_on.isoformat()} da "
                "boshlangan — o'chirish mumkin emas. Faqat hali boshlanmagan "
                "profil o'chiriladi."
            )

        result = await self.session.execute(
            delete(SnapshotSchedule)
            .where(
                SnapshotSchedule.market_id == self.market_id,
                SnapshotSchedule.id == schedule_id,
            )
            .returning(SnapshotSchedule.id)
        )
        return result.scalar_one_or_none() is not None

    # ------------------------------------------------------------------
    # Ichki yordamchilar
    # ------------------------------------------------------------------

    async def _profile_by_id(self, schedule_id: UUID) -> ScheduleProfile | None:
        """`id` bo'yicha profil; begona bozorniki bo'lsa `None` (RLS + predikat)."""
        result = await self.session.execute(
            self.scoped(
                select(
                    SnapshotSchedule.id,
                    SnapshotSchedule.name,
                    func.lower(SnapshotSchedule.period).label("starts_on"),
                    func.upper(SnapshotSchedule.period).label("ends_on"),
                ).where(SnapshotSchedule.id == schedule_id)
            )
        )
        row = result.one_or_none()
        if row is None:
            return None
        return ScheduleProfile(
            id=row.id,
            name=row.name,
            starts_on=row.starts_on,
            ends_on=row.ends_on,
            # `mode` bu yerda ATAYIN hisoblanmaydi: chaqiruvchi uni O'Z
            # `today` i bilan hisoblaydi (`_mode_of`). Bu yerda hisoblash
            # ikkinchi «bugun» manbaini tug'dirardi.
            mode=_ACTIVE,
        )

    async def _set_period(self, schedule_id: UUID, starts_on: date, ends_on: date | None) -> None:
        """Mavjud profilning davrini QAYTA QURADI.

        ⚠ Davr ustun darajasida tahrirlanmaydi (`upper(period)` ni SQL
          ichida almashtirish) — `assignment_period()` bilan QAYTA
          QURILADI. Sabab `vendor_repo.close()` da yozilgan: SQL ichidagi
          almashtirish chegara HARFINI matnga ikkinchi nusxa qilib
          ko'chirardi va konvensiya bir kun ikki joyda ajralib ketardi.
        """
        await self.session.execute(
            update(SnapshotSchedule)
            .where(
                SnapshotSchedule.market_id == self.market_id,
                SnapshotSchedule.id == schedule_id,
            )
            .values(period=assignment_period(starts_on, ends_on))
        )

    async def _restore_copy(self, source: ScheduleProfile, *, resumes_on: date) -> None:
        """Bo'lingan profilni `[resumes_on, eski_oxir)` da NUSXA sifatida tiklaydi."""
        copy_id = await self._insert_profile(
            source.name, assignment_period(resumes_on, source.ends_on)
        )
        await self.session.execute(
            _COPY_SLOTS,
            {"market_id": self.market_id, "target_id": copy_id, "source_id": source.id},
        )

    async def _insert_profile(self, name: str, period: object) -> UUID:
        result = await self.session.execute(
            insert(SnapshotSchedule)
            .values(
                # `market_id` REPOZITORIYDAN, so'rov tanasidan EMAS
                # (mass-assignment darvozasi — `nvr_repo` bilan bir xil qoida).
                market_id=self.market_id,
                name=name,
                period=period,
            )
            .returning(SnapshotSchedule.id)
        )
        return result.scalar_one()

    async def _insert_slots(self, schedule_id: UUID, slots: Sequence[time]) -> None:
        await self.session.execute(
            insert(SnapshotScheduleSlot).values(
                [
                    {
                        "market_id": self.market_id,
                        "schedule_id": schedule_id,
                        "slot_time": slot,
                    }
                    for slot in slots
                ]
            )
        )


def _mode_of(starts_on: date, ends_on: date | None, today: date) -> str:
    """Profilning BUGUNGA nisbatan rejimi (`04-UI-SPEC.md` §4.5).

    Chegaralar `[)` konvensiyasi bilan: `ends_on` KUNI profilga KIRMAYDI,
    ya'ni `ends_on == today` bo'lgan profil ALLAQACHON o'tmishda.
    """
    if starts_on > today:
        return _FUTURE
    if ends_on is not None and ends_on <= today:
        return _PAST
    return _ACTIVE


def _normalize(times: Iterable[time], max_times_per_day: int) -> tuple[time, ...]:
    """Vaqtlarni tekshiradi va O'SISH tartibida qaytaradi.

    ⚠ TARTIB DOMEN MA'NOSI TASHIMAYDI, shuning uchun u SHU YERDA
      normallashtiriladi. Klient tartibini saqlash «06:00, 18:00, 07:00»
      ko'rinishidagi ro'yxat berardi va UI har safar uni qayta saralashi
      kerak bo'lardi — ya'ni saralash mantig'i ikki joyda yashardi.

    ⚠ DUBLIKAT JIMGINA YUTILMAYDI, RAD ETILADI. `set()` ga aylantirish
      «qo'shdim, ko'rinmadi» tuyg'usini berardi (`04-UI-SPEC.md` §4.6 aynan
      shu sababdan dublikatni rad etadi).

    Raises:
        ScheduleSlotsInvalidError: bo'sh, dublikatli yoki chegaradan oshiq.
    """
    ordered = list(times)
    if not ordered:
        raise ScheduleSlotsInvalidError(
            "kamida bitta vaqt kerak — nol vaqt kadr olinmaydigan bozor degani"
        )
    if len(set(ordered)) != len(ordered):
        raise ScheduleSlotsInvalidError(f"vaqtlar takrorlangan: {sorted(ordered)}")
    if len(ordered) > max_times_per_day:
        raise ScheduleSlotsInvalidError(
            f"kuniga eng ko'pi {max_times_per_day} ta vaqt mumkin, berilgani {len(ordered)} ta"
        )
    return tuple(sorted(ordered))
