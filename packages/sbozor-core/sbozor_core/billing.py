"""Patta hisobining SOF QOIDALARI — hisob sharti, variance va taqsimlash.

=============================================================================
⛔⛔ BU MODUL UCHTA MUSTAQIL SAVOLNI HAL QILADI VA CHEGARALARI MEXANIK.

    1-savol — HISOB YOZILADIMI? (`billable_from_slots`)
              «kamida 2 slotda band, YOKI 1 slot band + O'SHA slotda
              nazoratchi tasdig'i» (BILL-01, D-04/D-05, C-6).

    2-savol — DEKLARATSIYA TIZIMDAN QANCHA FARQ QILADI? (`variance`)
              Belgili son, IKKI TOMONLAMA (CASH-04, D-26).

    3-savol — QAYSI KUNNING PATTASI TO'LANDI? (`allocate_charge_credit`,
              `total_due_soum`, `payment_quote_set`)
              Nomlangan, determinlashtirilgan, SAQLANMAYDIGAN taqsimlash
              (D-24, BILL-03, UI-SPEC §9.4/§9.6).

⛔ 1-daraja (kameralararo) va 2-daraja (slotlararo) CHEGARASI:
   kameralararo agregatsiya `sbozor_core/occupancy.py` da TUGAGAN va u
   yerda ochiq yozilgan («2-daraja — 6-FAZANING qoidasi va u bu yerda
   YOZILMAYDI»). Bu modul o'sha va'daning IKKINCHI yarmi: slotlararo
   qoida faqat shu yerda yashaydi. Ikki nusxa ajralib ketganda direktor
   bandlik sahifasida bitta son, patta hisobida boshqa son ko'rardi — va
   ikkalasi ham «to'g'ri» bo'lardi.

⛔ SQL BU QOIDALARNI TAKRORLAMAYDI, CHAQIRADI. `billing_repo` (06-06) va
   `POST /payments` (06-09) shu funksiyalarni ishlatadi; predikatni SQL
   da ikkinchi marta yozish D-16 ning «ikki haqiqat manbai» sinfini
   qaytarardi (bu loyihada takroran topilgan).

=============================================================================
⚠⚠ MODULNING BOG'LIQLIGI YO'Q — NA DB, NA HTTP, NA NAVBAT.

`sbozor_core/__init__.py` «biznes logikasi yo'q» deydi; bu modul o'sha
chegarani `occupancy.py` bilan AYNI maqomda ANIQLASHTIRADI: bu yerda
faqat sof, kirish-chiqishsiz domen arifmetikasi yashaydi (`money.py` va
`periods.py` bilan bir xil sinf).

⛔ PUL — BUTUN SO'M (`BIGINT` ↔ `int`), D-11. Kasrli tiplar (`float` va
   o'nlik kasr sinfi) BU MODULDA UMUMAN UCHRAMAYDI va bu MEXANIK
   qulflangan: `06-01-PLAN.md` ning qabul mezoni fayl matnini grep bilan
   tekshiradi. Sabab mahsulotning o'zagida — yaxlitlanish drifti aynan
   SBOZOR oldini olish uchun mavjud bo'lgan nizoni tug'diradi.
=============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from sbozor_core.enums import OccupancyVerdict, ResolutionSource
from sbozor_core.money import assert_safe_soum

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import date

__all__ = (
    "ALLOCATION_RULE",
    "BillableDecision",
    "ChargeAllocationRow",
    "ChargeCreditAllocation",
    "ChargeDue",
    "allocate_charge_credit",
    "billable_from_slots",
    "payment_quote_set",
    "total_due_soum",
    "variance",
)
"""⛔ EKSPORT YUZASI — BESH FUNKSIYA, TO'RT TIP VA BITTA QOIDA NOMI.

Kortej ATAYIN (ro'yxat emas), `occupancy.py:77-82` bilan aynan bir xil
sabab: yuzani kengaytirish MANBA MATNINI o'zgartirishni talab qiladi,
ya'ni u ko'rinadigan qarorga aylanadi. `.append()` bilan «vaqtincha»
qo'shib qo'yish imkonsiz.
"""


ALLOCATION_RULE: Final[str] = "FIFO_OLDEST_SERVICE_DATE_FIRST"
"""⛔ TAQSIMLASH QOIDASINING NOMI — D-24 ning javobi SHU SATRDAN boshlanadi.

Hisobotlar, keyingi fazalar va nizo hujjatlari qoidaga **NOM BILAN**
murojaat qiladi, «bizda shunday hisoblanadi» deb emas. Nom `payments`
javobida ham, `vendor_charge_allocation()` (06-06) ning chiqishida ham
qaytariladi.

MA'NOSI: sotuvchining belgili krediti eng QADIMGI to'lanmagan
`daily_charges.service_date` dan boshlab yopiladi; bir kunda ikki rasta
bo'lsa tenglik `stall_code` bo'yicha O'SISH tartibida uziladi.

⚠ NEGA UMUMAN NOM KERAK: `payments.charge_id` IMKONSIZ (C-4 — to'lov
paytida hisob hali tug'ilmagan, C-3; va bitta to'lov BIR NECHA kunlik
qarzni yopadi, UI-SPEC §9.6). `service_date` yolg'iz o'zi ham yetarli
emas — `[Qarzni ham olish]` da u BUGUN bo'lib qoladi, holbuki to'langan
kunlar ESKI. Ya'ni javob ustunda emas, QOIDADA yashaydi va qoida
nomlanmasa u har hisobotda qaytadan ixtiro qilinardi.
"""


_OCCUPIED: Final[str] = OccupancyVerdict.OCCUPIED.value
_HUMAN: Final[str] = ResolutionSource.HUMAN.value
_NO_COVERAGE: Final[str] = ResolutionSource.NO_COVERAGE.value

_ALLOWED_VERDICTS: Final[frozenset[str]] = frozenset(
    {
        OccupancyVerdict.OCCUPIED.value,
        OccupancyVerdict.EMPTY.value,
        OccupancyVerdict.UNCERTAIN.value,
        _NO_COVERAGE,
    }
)
"""`stall_slot_occupancy.verdict` ning TO'RT qiymati.

⚠ `no_coverage` `OccupancyVerdict` DA YO'Q va bu ataylab: u zona verdikti
emas, zonalarning YO'QLIGI (`occupancy.py:131-138`). Materializatsiya
qilingan slot qatorida esa u HAM verdikt, HAM manba bo'lib turadi, ya'ni
bu funksiya uni qabul qilishi SHART — aks holda qamrovsiz rasta
`ValueError` bilan butun kun yopilishini yiqitardi.
"""

_ALLOWED_SOURCES: Final[frozenset[str]] = frozenset(item.value for item in ResolutionSource)


def _reject_unknown(value: str, allowed: frozenset[str], *, kind: str) -> str:
    """Noma'lum qiymatni OCHIQ rad etadi (`occupancy.py::_rank` bilan bir qoida).

    Domen funksiyasi noma'lum verdikt bilan JIMGINA ishlashi eng yomon
    variant: u shartni tasodifiy hal qilib, patta hisobini jimgina
    buzardi va nosozlik faqat sotuvchi bilan nizoda ko'rinardi (D-02).
    """
    if value not in allowed:
        raise ValueError(
            f"billable_from_slots(): noma'lum {kind}: {value!r}. "
            f"Ruxsat etilganlari: {sorted(allowed)}."
        )
    return value


# ===========================================================================
# 1-SAVOL — HISOB YOZILADIMI (BILL-01, D-04/D-05, C-6)
# ===========================================================================


@dataclass(frozen=True, slots=True)
class BillableDecision:
    """Bir RASTANING bir KUNDAGI hisob qarori — ⛔ NOL EMAS, NATIJA.

    Hamma maydon HAR DOIM qaytariladi va bu ataylab: chaqiruvchi
    `billable` ni ko'rib «nega?» deb qayta hisoblashga majbur bo'lmasin.
    Sanoqlar hisobotga ham, `billing_anomalies` qaroriga ham kerak.

    slots:                   qaralgan slot qatorlari soni (jami)
    occupied_slots:          `verdict = 'occupied'` bo'lgan slotlar (D-05)
    human_confirmed_occupied: AYNI slotda `occupied` VA `human` (C-6)
    no_coverage_slots:       `resolution_source = 'no_coverage'` slotlar
    billable:                D-04 predikatining natijasi
    no_coverage_only:        BARCHA slotlar qamrovsiz (D-05, anomaliya EMAS)
    """

    slots: int
    occupied_slots: int
    human_confirmed_occupied: bool
    no_coverage_slots: int
    billable: bool
    no_coverage_only: bool


def billable_from_slots(slots: Sequence[tuple[str, str]]) -> BillableDecision:
    """Bir rasta, bir kun — kunlik patta hisobi yoziladimi (BILL-01).

    =======================================================================
    ⛔ D-04 — HISOB SHARTI:

        occupied_slots >= 2
        YOKI (occupied_slots >= 1 VA human_confirmed_occupied)

    Bitta TASDIQLANMAGAN AI sloti hisob BERMAYDI — noaniqlik sotuvchi
    foydasiga hal qilinadi (`06-CONTEXT.md` D-04).
    =======================================================================
    ⛔⛔ C-6 — `human_confirmed_occupied` AYNI SLOTNI TALAB QILADI.

    `occupancy_repo.py:369` dagi mavjud ustun BOSHQA savolga javob beradi:

        bool_or(sso.resolution_source = 'human')  AS human_confirmed

    U `verdict` bilan BOG'LANMAGAN. Ya'ni rasta 1 slotda AI-`occupied`,
    BOSHQA slotda nazoratchi «BO'SH» degan bo'lsa ham `occupied_slots = 1
    AND human_confirmed = true` chiqadi va D-04 hisob YOZARDI — holbuki
    hech kim bandlikni tasdiqlamagan. Bu JIM NOTO'G'RI HISOB va u aynan
    D-02 ning nizo sinfi: sotuvchi to'lamagan patta uchun qarzdor bo'ladi.

    ⛔ SHUNING UCHUN IKKI SHARTNI ALOHIDA `any()` BILAN HISOBLASH
       TAQIQLANADI. To'g'ri shakl — bitta qatordagi KONYUNKSIYA:

           any(v == 'occupied' and s == 'human' for v, s in slots)

    `occupancy_repo` ning `human_confirmed` ustuni HISOBOTDA QOLADI va
    billingda ISHLATILMAYDI — u «nechta rasta nazoratchi ko'zi bilan hal
    qilindi?» degan boshqa savolning javobi.
    =======================================================================
    ⛔ D-05 — `no_coverage` SANOQQA UMUMAN KIRMAYDI.

    Qamrovsiz slot NA `occupied`, NA «bo'sh». `no_coverage_only` — barcha
    slotlari qamrovsiz bo'lgan rasta uchun ALOHIDA bayroq va u
    ⛔ **BILL-04 anomaliyasi EMAS**: «ko'ra olmadik» ≠ «band, lekin
    biriktirilmagan». Ikkisini bir joyga qo'shish KO'R NUQTADAN TUSHUM
    DA'VOSI TO'QISH bo'lardi (0-fazadagi ~10 % qamrovsizlik aynan shu
    bayroq ostida ko'rinadi).

    ⚠ JUFTLIK INVARIANTI (`(verdict = 'no_coverage') = (resolution_source
      = 'no_coverage')`) BU YERDA TAKRORLANMAYDI — u `stall_slot_occupancy`
      ning `CHECK` ida (05-05) va ikkinchi nusxa sxemadan jimgina ajralib
      ketardi. Qamrov savoliga bu yerda `resolution_source` javob beradi.
    =======================================================================
    ⛔ BO'SH KIRISH — UCHINCHI HOLAT (`no_slot_rows`), `no_coverage_only`
       EMAS.

    `slots == 0` degani «bu rasta uchun bu kunda materializatsiya
    qilingan qator UMUMAN yo'q» (C-3 / Pitfall 2 — `stall_slot_occupancy`
    BUGUNGI kun uchun bo'sh, u kechqurun `day_close` da to'ladi).
    `no_coverage_only` esa «qatorlar BOR, lekin hech biri qamramagan».
    Ikkisini bir bayroqqa siqish `billing_close` ni hali yopilmagan kun
    ustida yugurtirganda «hamma rasta qamrovsiz» degan YOLG'ON hisobot
    berardi.

    Args:
        slots: shu rastaning shu kundagi `stall_slot_occupancy` qatorlari,
            har biri `(verdict, resolution_source)` juftligi (xom `str` —
            qiymat to'g'ridan-to'g'ri ustundan keladi).

    Returns:
        `BillableDecision` — hamma maydon to'ldirilgan holda.

    Raises:
        ValueError: verdikt yoki manba ruxsat etilgan to'plamdan tashqarida.
    """
    occupied_slots = 0
    no_coverage_slots = 0
    human_confirmed_occupied = False

    for verdict, source in slots:
        _reject_unknown(verdict, _ALLOWED_VERDICTS, kind="slot verdikti")
        _reject_unknown(source, _ALLOWED_SOURCES, kind="slot manbai")

        if verdict == _OCCUPIED:
            occupied_slots += 1
            # ⛔ C-6: shart AYNI SLOTDA, ikki alohida `any()` da EMAS.
            if source == _HUMAN:
                human_confirmed_occupied = True

        if source == _NO_COVERAGE:
            no_coverage_slots += 1

    total = len(slots)
    billable = occupied_slots >= 2 or (occupied_slots >= 1 and human_confirmed_occupied)

    return BillableDecision(
        slots=total,
        occupied_slots=occupied_slots,
        human_confirmed_occupied=human_confirmed_occupied,
        no_coverage_slots=no_coverage_slots,
        billable=billable,
        no_coverage_only=total > 0 and no_coverage_slots == total,
    )


# ===========================================================================
# 2-SAVOL — DEKLARATSIYA FARQI (CASH-04, D-26)
# ===========================================================================


def variance(declared_soum: int, system_soum: int) -> int:
    """Ko'r deklaratsiya farqi — ⛔ BELGILI son, IKKI TOMONLAMA (D-26).

    =======================================================================
    ⛔ `declared_soum - system_soum` NATIJASI `assert_safe_soum()` DAN
       O'TKAZILMAYDI VA MODULGA (musbat kattalikka) AYLANTIRILMAYDI.

    KAMOMAD (`< 0`) ham, ORTIQCHA (`> 0`) ham MA'NO TASHIYDI. Ortiqcha
    naqdni jimgina yutish kamomadni yashirish bilan BIR XIL xato: ikkalasi
    ham «kassa hisobi mos kelmadi» degan bitta signalning ikki yo'nalishi
    va direktor ularni AJRATIB ko'rishi kerak.

    `money.py:87-101` (`format_soum`) aynan shu sababdan manfiy qiymatni
    KO'RSATISH uchun qabul qiladi, `assert_safe_soum()` esa (`:65-84`)
    SAQLASH uchun rad etadi. Bu funksiya SAQLANMAYDIGAN hosila beradi —
    ya'ni u `format_soum` tomonida.

    ⚠ `abs` funksiyasi bu modulda umuman uchramaydi va bu MEXANIK
      qulflangan (`06-01-PLAN.md` qabul mezoni fayl matnini grep qiladi).
      Ishorani yo'qotish D-26 ni bitta chaqiruv bilan bekor qilardi.
    =======================================================================

    Args:
        declared_soum: kassir SANAB kiritgan naqd (0 RUXSAT — butun smena
            terminal bo'lgan kun real holat, UI-SPEC §10.2).
        system_soum: shu smenaga bog'langan to'lovlarning tizim yig'indisi.

    Returns:
        `declared - system` — belgili `int`. Manfiy = KAMOMAD,
        musbat = ORTIQCHA.

    Raises:
        TypeError: kirishlardan biri kasrli yoki mantiqiy tipda (D-11).
        ValueError: kirishlardan biri manfiy yoki xavfsiz chegaradan katta.
    """
    assert_safe_soum(declared_soum)
    assert_safe_soum(system_soum)
    return declared_soum - system_soum


# ===========================================================================
# 3-SAVOL — QAYSI KUNNING PATTASI TO'LANDI (D-24, BILL-03)
# ===========================================================================


def _assert_signed_soum(value: int) -> int:
    """Belgili pul — MANFIY RUXSAT (avans), kasrli/mantiqiy tip TAQIQ.

    ⛔ IKKINCHI TIP QOIDASI YOZILMAYDI. Ikkala shox ham qiymatni
       `assert_safe_soum()` ga OLIB BORADI (manfiy shoxda teskari ishora
       bilan), ya'ni «pul nima bo'la oladi» savoliga javob `money.py` da
       YOLG'IZ qoladi. Bu yerda ikkinchi `isinstance` zanjiri yozilsa u
       `money.py` dan jimgina ajralib ketardi.

    ⚠ MANFIY QIYMAT NEGA RUXSAT: ortiqcha to'lov (avans) OQ-4/A4 bo'yicha
      ATAYIN qabul qilinadi va u `outstanding_soum < 0` bo'lib keladi.
      Bloklash kassirni pulni UMUMAN YOZMASLIKKA majburlardi — ya'ni
      himoya o'zi himoya qilayotgan yozuvni yo'q qilardi.
    """
    if value < 0:
        assert_safe_soum(-value)
        return value
    assert_safe_soum(value)
    return value


def total_due_soum(today_soum: int | None, outstanding_soum: int) -> int:
    """Bugungi tarif + eski qarz — ⛔ SERVERDAGI YAGONA QO'SHISH AMALI.

    =======================================================================
    ⛔ IKKI CHAQIRUVCHI, BITTA FUNKSIYA:

        pending_projection()   (06-06, UI-SPEC §9.2 ning `total_due_soum`)
        POST /payments         (06-09, kvota to'plamining uchinchi elementi)

    Ikkalasi ham SHU funksiyani chaqiradi. Qo'shish amali ikki joyda
    yozilsa ular BIR KUN ajralib ketardi (bu loyihada takroran topilgan
    sinf: D-16, 04-10, 05-14) va UI-SPEC §9.6 ning «klientda arifmetika
    YO'Q» qarori serverda IKKI HAQIQAT MANBAI bilan almashardi — ya'ni
    xato klientdan serverga KO'CHARDI, yo'qolmasdi.
    =======================================================================

    Args:
        today_soum: bugungi tarif summasi, yoki `None` — «summa yo'q»
            (`market_closed` / `tariff_missing`, UI-SPEC §9.4).
        outstanding_soum: eski qarz. ⚠ MANFIY bo'lishi mumkin (avans).

    Returns:
        Belgili `int`. `today_soum is None` -> faqat qarz.
    """
    today = 0 if today_soum is None else assert_safe_soum(today_soum)
    _assert_signed_soum(outstanding_soum)
    return today + outstanding_soum


def payment_quote_set(
    today_soum: int | None,
    outstanding_soum: int,
    fee_soum: int = 0,
) -> tuple[int, ...]:
    """Serverning ASOSLANGAN takliflari — ⛔ USTUVORLIK tartibida (UI-SPEC §9.4/§9.6).

    =======================================================================
    TARTIB NUMERIK EMAS, USTUVORLIK BO'YICHA:

        1. today_soum             — bugungi TO'LIQ patta: rasta + tarozi
                                    (STANDART tanlov, §9.6)
        2. today_soum − fee       — ⛔ FAQAT RASTA PULI; xizmat haqi
                                    (tarozi) qarzga qoladi (0027)
        3. outstanding_soum       — ⛔ FAQAT eski qarz (§9.4 ning «Faqat
                                    `outstanding_soum`» ustuni)
        4. total_due_soum()       — `[Qarzni ham olish]` (§9.6)

    =======================================================================
    ⛔⛔ NEGA (2) TAKLIFLAR TO'PLAMIDA — VA NEGA U OVERRIDE EMAS (0027).

    Tarozi to'lovi kassir kartasida STANDART BELGILANGAN keladi. Kassir
    belgini olib tashlaganda u faqat rasta pulini yozadi va tarozi puli
    QARZ bo'lib qoladi — bu MAHSULOT tomonidan ko'zda tutilgan NORMAL
    yo'l, istisno emas.

    Bu summa takliflar to'plamiga KIRMASA, `POST /payments` uni «asossiz»
    deb ko'rib sabab kodi TALAB QILARDI (`reason_required`, 06-09 ning
    5-qadami). Ya'ni kuniga yuzlab marta takrorlanadigan oddiy harakat
    DL-1 (override) dialogidan o'tardi — 06-fazada aynan shu naqsh
    «NORMAL HOLAT ISTISNO YO'LIDAN o'tadi» degan dizayn xatosi sifatida
    nomlangan (pastdagi §9.6 izohi).

    ⚠ (1) BIRINCHI BO'LIB QOLADI: `quotes[0]` override paytidagi zaxira
      taklif va u TO'LIQ patta bo'lishi shart — aks holda sabab bilan
      kiritilgan summa tarozisiz taklifga solishtirilardi.

    ⚠ `fee_soum = 0` bo'lganda (2) == (1) va dublikat filtri uni OLIB
      TASHLAYDI — xizmat haqisiz bozorda to'plam BAYT-BA-BAYT
      o'zgarishsiz qoladi.
    =======================================================================

    ⚠ NEGA STANDART FAQAT BUGUNGI PATTA: kassirning kunlik ishi bugungi
      pattani yig'ish. Standart `total_due_soum` bo'lsa 45 000 qarzi bor
      sotuvchi bugungi 15 000 ni <=3 bosishda to'lay olmasdi va kassir
      DL-1 (override) ga majbur bo'lardi — ya'ni NORMAL HOLAT ISTISNO
      YO'LIDAN o'tardi (§9.6, dizayn xatosi).
    =======================================================================
    ⛔ QAT'IY MUSBAT FILTRI VA DUBLIKAT OLIB TASHLASH:

      * element `> 0` bo'lmasa to'plamga KIRMAYDI (nol yoki manfiy summa
        to'lov emas);
      * dublikat BIRINCHI UCHRASHI bo'yicha olib tashlanadi —
        `outstanding_soum == 0` bo'lganda (1) va (3) TENG bo'ladi va
        ekranda ikkita bir xil tugma chizilardi.

    ⛔ BO'SH NATIJA (`()`) MA'NOLI VA U 06-09 NING YAGONA 422 YO'LI:
    «bu rastaga bugun asoslangan to'lov yo'q». ⚠ Shart AYNAN shu —
    «bugungi summa yo'q» EMAS (G-15): yopiq kunda ham, tarifi
    belgilanmagan rastada ham eski QARZ undirilishi SHART, aks holda
    `market_closed` qarzni undirilmaydigan qilib qo'yardi.

    Args:
        today_soum: bugungi TO'LIQ patta (rasta + tarozi) yoki `None`
            (§9.4 ning ikki sababi).
        outstanding_soum: eski qarz; ⚠ MANFIY bo'lishi mumkin (avans),
            shuning uchun unga `assert_safe_soum()` QO'LLANILMAYDI.
        fee_soum: `today_soum` ICHIDAGI majburiy xizmat haqi (tarozi)
            ulushi. ⛔ Standart `0` — chaqiruvchi uni bermasa xulq 0027
            dan OLDINGIDEK qoladi.

    Returns:
        Ustuvorlik tartibida, dublikatsiz, faqat qat'iy musbat takliflar.
    """
    fee = assert_safe_soum(fee_soum)
    today = 0 if today_soum is None else assert_safe_soum(today_soum)

    candidates = (
        today,
        # ⛔ AYIRISH FAQAT `today` MAVJUD BO'LGANDA MA'NOLI: `today == 0`
        #   (yopiq kun / tarifsiz rasta) bo'lganda «rasta puli» degan
        #   tushunchaning o'zi yo'q va manfiy nomzod filtrdan o'tmasdi
        #   ham — shart baribir ATAYIN yozilgan, chunki u NIYATNI
        #   ko'rsatadi, filtrga tayanish esa tasodifga tayanish bo'lardi.
        today - fee if today > 0 else 0,
        _assert_signed_soum(outstanding_soum),
        total_due_soum(today_soum, outstanding_soum),
    )

    quotes: list[int] = []
    for amount in candidates:
        if amount > 0 and amount not in quotes:
            quotes.append(amount)
    return tuple(quotes)


@dataclass(frozen=True, slots=True)
class ChargeDue:
    """Bitta kunlik hisob — ⛔ TUZATISHLAR BILAN OLDINDAN NETLANGAN.

    `due_soum` = `daily_charges.amount_soum` + shu hisobga tegishli
    `charge_adjustments` ning BELGILI yig'indisi. Netlashni CHAQIRUVCHI
    bajaradi (`billing_repo`, 06-06) va bu ataylab: tuzatishlarni bu
    funksiya ichida yig'ish uni jadval strukturasiga bog'lab qo'yardi,
    holbuki u SOF qoladi.

    `stall_code` — tenglik uzgichi (bir kunda bir sotuvchida ikki rasta
    bo'lishi NORMAL). U `stall_id` EMAS: kod hisobotda ham, nizoda ham
    odam o'qiydigan yorliq, UUID esa tartibni tasodifiy qilardi.
    """

    service_date: date
    stall_code: str
    due_soum: int


@dataclass(frozen=True, slots=True)
class ChargeAllocationRow:
    """Bir hisobga tushgan kredit — ⛔ NOL EMAS, NATIJA (hamma maydon bor)."""

    service_date: date
    stall_code: str
    due_soum: int
    paid_soum: int
    unpaid_soum: int
    settled: bool


@dataclass(frozen=True, slots=True)
class ChargeCreditAllocation:
    """`FIFO_OLDEST_SERVICE_DATE_FIRST` ning natijasi — HOSILA KO'RINISH.

    `rule` natijaning O'ZIDA qaytariladi: hisobot yoki nizo hujjati
    «qaysi qoida bo'yicha?» degan savolga javobni YONIDA topadi, boshqa
    faylni izlab yurmaydi.

    `rows` — KORTEJ (ro'yxat emas): natija o'zgarmas va u ikki chaqiruvni
    bayt-bayt solishtirish (determinizm testi) uchun ham kerak.
    """

    rule: str
    rows: tuple[ChargeAllocationRow, ...]
    advance_soum: int
    unpaid_soum: int


def allocate_charge_credit(
    charges: Sequence[ChargeDue],
    credit_soum: int,
) -> ChargeCreditAllocation:
    """⛔ D-24 NING MEXANIZMI — «qaysi kunning pattasi to'landi?» ning javobi.

    =======================================================================
    ⛔⛔ NATIJA HECH QAYERGA SAQLANMAYDI.

    Bu funksiya HOSILA KO'RINISH hisoblaydi. `payment_allocations` degan
    jadval YO'Q va QO'SHILMAYDI; `allocated_*` ustuni ham tug'ilmaydi.
    Sabab D-07 / BILL-03: qoldiq HAR DOIM hisoblanadi
    (hisoblar − to'lovlar + tuzatishlar) va SAQLANGAN BALANS umuman
    mavjud emas. «Tezlik uchun» taqsimlashni jadvalga yozib qo'yish
    ayni shu shartni buzardi va ikkinchi haqiqat manbai tug'dirardi —
    bu taqiq shu yerda ATAYIN yozilgan, chunki vasvasa keyingi ijrochida
    tug'iladi.
    =======================================================================
    ⛔ TARTIB `sorted()` BILAN, KIRITISH TARTIBIGA TAYANMAYDI.

    Kalit — `(service_date, stall_code)` O'SISH bo'yicha. Bir sotuvchida
    bir kunda IKKI RASTA bo'lishi normal, ya'ni tenglik uzilishi
    determinlashtirilmasa AYNI KIRISH IKKI XIL javob berardi (SQL
    `ORDER BY` siz qatorlarni ixtiyoriy tartibda qaytaradi). Nizoda
    bunday javob ⛔ DALIL QIYMATINI YO'QOTARDI — D-02 ning butun sharti
    aynan shu.
    =======================================================================
    ⛔ IKKI INVARIANT FUNKSIYANING O'ZIDA MAJBURLANADI (jim noto'g'ri
       natija EMAS):

        (a) Σ paid + advance_soum == max(credit_soum, 0)
            -> kredit YO'QOLMAYDI: har so'm yo hisobga tushgan, yo avans.

        (b) unpaid_soum == max(Σ due − max(credit_soum, 0), 0)
            -> ⛔ bu `vendor_outstanding()` (BILL-03) BILAN BIR XIL SON.
            Hosila ko'rinish hisoblanadigan qoldiqdan AJRALIB KETA
            OLMAYDI: taqsimlash boshqa raqam ko'rsatsa, ekrandagi qarz
            bilan hisobotdagi qarz bir kun farq qilardi va ikkalasi ham
            «to'g'ri» bo'lardi.

    ⚠ INVARIANTLAR `AssertionError` BILAN, `assert` BAYONOTI bilan EMAS —
      IKKI SABAB, ikkalasi ham mustaqil: (1) `assert` `python -O` da
      BUTUNLAY olib tashlanadi, ya'ni nazorat aynan ishlab chiqarish
      rejimida yo'qolardi; (2) ruff `S101` uni mahsulot kodida taqiqlaydi
      (`pyproject.toml` faqat `tests/**` ga istisno beradi). Tip esa
      ATAYIN `AssertionError`: bu chaqiruvchi tekshiradigan kirish sharti
      EMAS, funksiyaning O'Z arifmetikasining nazorati — buzilishi dastur
      nosozligini bildiradi, foydalanuvchi xatosini emas.
    =======================================================================

    Args:
        charges: sotuvchining to'lanmagan (yoki qisman to'langan)
            hisoblari; tartib AHAMIYATSIZ.
        credit_soum: to'lovlarning BELGILI yig'indisi —
            `CASE WHEN kind = 'reversal' THEN -amount_soum ELSE
            amount_soum END`. ⚠ Storno netlashgach 0 yoki manfiy
            bo'lishi mumkin; funksiya YIQILMAYDI.

    Returns:
        `ChargeCreditAllocation` — qoida nomi, qatorlar, avans va qoldiq.

    Raises:
        TypeError: pul qiymatlaridan biri kasrli/mantiqiy tipda (D-11).
        ValueError: `due_soum` manfiy (u qarz emas — o'ta katta `decrease`
            D-07 ning o'z savoli, taqsimlash qoidasiniki emas).
    """
    _assert_signed_soum(credit_soum)
    for charge in charges:
        assert_safe_soum(charge.due_soum)

    ordered = sorted(charges, key=lambda charge: (charge.service_date, charge.stall_code))

    # Manfiy kredit (storno netlashdan keyin) HECH NIMANI yopmaydi, lekin
    # funksiyani ham yiqitmaydi — `max(..., 0)` aynan shu holat uchun.
    remaining = max(credit_soum, 0)
    initial = remaining

    rows: list[ChargeAllocationRow] = []
    for charge in ordered:
        paid = min(max(remaining, 0), charge.due_soum)
        remaining -= paid
        rows.append(
            ChargeAllocationRow(
                service_date=charge.service_date,
                stall_code=charge.stall_code,
                due_soum=charge.due_soum,
                paid_soum=paid,
                unpaid_soum=charge.due_soum - paid,
                settled=paid == charge.due_soum,
            )
        )

    advance = max(remaining, 0)
    paid_total = sum(row.paid_soum for row in rows)
    unpaid = sum(row.unpaid_soum for row in rows)
    total_due = sum(charge.due_soum for charge in charges)

    # (a) kredit yo'qolmaydi
    if paid_total + advance != initial:
        raise AssertionError(
            "allocate_charge_credit(): kredit yo'qoldi — "
            f"Σ paid ({paid_total}) + advance ({advance}) != max(credit, 0) ({initial})"
        )
    # (b) `vendor_outstanding()` (BILL-03) bilan BIR XIL son
    if unpaid != max(total_due - initial, 0):
        raise AssertionError(
            "allocate_charge_credit(): hosila taqsimlash hisoblanadigan qoldiqdan "
            f"ajralib ketdi — unpaid ({unpaid}) != max(Σ due − max(credit, 0), 0) "
            f"({max(total_due - initial, 0)})"
        )

    return ChargeCreditAllocation(
        rule=ALLOCATION_RULE,
        rows=tuple(rows),
        advance_soum=advance,
        unpaid_soum=unpaid,
    )
