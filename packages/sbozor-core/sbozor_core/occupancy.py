"""Bandlik agregatsiyasi — BIR RASTA, BIR SLOT, BIR NECHA KAMERA (AI-05).

=============================================================================
⛔⛔ BU MODUL AYNAN BITTA DARAJANI BIRLASHTIRADI VA CHEGARA MEXANIK.

    1-daraja — KAMERALARARO: bir rasta, bir slot, bir necha kamera.
               «Birortasi band desa — rasta band» (AI-05, D-20).
               ⟵ SHU MODUL, va faqat shu.

    2-daraja — SLOTLARARO: bir rasta, bir kun, yetti slot.
               «kamida 2 slotda band, yoki 1 slot + nazoratchi tasdig'i»
               (BILL-01) — 6-FAZANING qoidasi va u bu yerda YOZILMAYDI.

Chegara ochiq yozilmasa 5-faza bilmasdan billing qoidasini amalga oshirib
qo'yardi va 6-faza uni IKKINCHI marta yozardi. Ikki nusxa ajralib
ketganda direktor bandlik sahifasida bitta son, patta hisobida boshqa
son ko'rardi — va ikkalasi ham «to'g'ri» bo'lardi.

⚠ CHEGARA `__all__` BILAN USHLAB TURILADI VA U KORTEJ (ro'yxat EMAS).
  Ro'yxatga ikkinchi daraja funksiyasini «vaqtincha» `.append()` bilan
  qo'shib qo'yish mumkin bo'lardi; kortejda esa eksport yuzasini
  kengaytirish MANBA MATNINI o'zgartirishni talab qiladi, ya'ni u
  ko'rinadigan qarorga aylanadi. `tests/unit/test_aggregate_stall_slot.py`
  ikkala nomni ham runtime'da sanaydi.
=============================================================================

USTUVORLIK TALABDAGIDAN UZUNROQ — VA UZAYTIRISH D-22 NING O'ZI.

    occupied  >  uncertain  >  empty  >  no_coverage

AI-05 faqat birinchi bandni talab qiladi («birortasi band desa band»).
Qolgan uchtasi kerak, chunki §A.3 dagi `no_coverage` MAVJUD holat va u
«bo'sh» EMAS: uni «bo'sh» ga qo'shish O'LCHOVNING YO'QLIGINI yaxshi
natijaga aylantirardi — qamrovsiz rasta hisobotda «bo'sh» bo'lib
ko'rinib, jimgina yo'qotishga aylanardi (D-22).

`uncertain` o'rtada turadi, chunki u «model bilmaydi» degani, «bo'sh»
degani emas: bir kamera ikkilanib, ikkinchisi bo'sh desa, rasta haqidagi
javob hamon ochiq.

=============================================================================
⚠⚠ `effective` VERDIKTLAR BIRLASHTIRILADI, XOM AI VERDIKTLARI EMAS.

Nazoratchi 2-kamerada «bo'sh» deb tasdiqlagan bo'lsa ham, 1-kameraning
AI «band» i BARIBIR g'olib bo'ladi. Bu xato emas — rasta bir kamerada
ko'rinib, ikkinchisida burchak yoki to'siq tufayli ko'rinmasligi mumkin.
Inson qarori O'SHA KAMERANING zonasini almashtiradi, agregatsiya
qoidasini EMAS (§D.11).

=============================================================================
MODULNING BOG'LIQLIGI YO'Q — NA DB, NA HTTP, NA NAVBAT.

`sbozor_core/__init__.py` «biznes logikasi yo'q» deydi va bu modul o'sha
chegarani KENGAYTIRMAYDI, balki ANIQLASHTIRADI: bu yerda faqat sof,
kirish-chiqishsiz domen arifmetikasi yashaydi (`money.py` va
`periods.py` bilan bir xil maqom). DB ga, HTTP ga yoki navbatga tegadigan
hech nima bu paketga kirmaydi.

⚠ BUGUN IMPORT QILUVCHI AYNAN BITTA — `core-api` ning kun yopilishi
  (`app/jobs/day_close.py`) va aniqlik hisoboti. «`cv-service` ham
  import qiladi» degan da'vo BUGUN YOLG'ON bo'lardi: `detect` zona
  darajasida yozadi va rasta darajasiga umuman ko'tarilmaydi. Joylashuv
  baribir shu yerda, chunki 6-faza (billing) va `cv-service` ning
  kelajakdagi krop-klassifikatori ayni shu funksiyaga muhtoj bo'ladi —
  va o'shanda ikkinchi nusxa TUG'ILMASLIGI kerak.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from sbozor_core.enums import OccupancyVerdict, ResolutionSource

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ("aggregate_stall_slot", "effective_verdict")
"""⛔ EKSPORT YUZASI AYNAN IKKI FUNKSIYA — modul docstringidagi chegara.

Kortej ATAYIN (ro'yxat emas): ikkinchi daraja agregatsiyasini bu yerga
qo'shish uchun manba matnini o'zgartirish kerak bo'ladi.
"""


_VERDICT_PRIORITY: Final[tuple[str, ...]] = (
    OccupancyVerdict.OCCUPIED.value,
    OccupancyVerdict.UNCERTAIN.value,
    OccupancyVerdict.EMPTY.value,
)
"""Zona verdiktlarining ustuvorligi — birinchisi eng kuchli (D-20).

⚠ `no_coverage` BU RO'YXATDA YO'Q va bu ataylab: u ZONA verdikti emas,
  u zonalarning YO'QLIGI. Uni bu yerga qo'shish «qamrovsiz zona» degan
  ifodalab bo'lmaydigan holatni qonuniylashtirardi.
"""

_SOURCE_STRENGTH: Final[tuple[str, ...]] = (
    ResolutionSource.HUMAN.value,
    ResolutionSource.AI.value,
    ResolutionSource.DEFAULT_EMPTY.value,
)
"""G'olib verdikt ichidagi TENGLIKNI buzadigan tartib — birinchisi eng KUCHLI DALIL.

=============================================================================
⚠⚠ REJA BU TARTIBNI BELGILAMAYDI, LEKIN UNSIZ NATIJA KIRISH TARTIBIGA
   BOG'LIQ BO'LARDI — ya'ni bitta rastaning hisobotdagi o'rni zonalar
   qaysi navbatda o'qilganiga qarab o'zgarardi. Bu JIM nosozlik:
   hisoblagichlar to'g'ri yig'iladi, faqat noto'g'ri kataklarga tushadi.

QARAMA-QARSHI IKKI QOIDA VA TANLOVNING SABABI:

  «ENG KUCHSIZ DALIL YUTADI» (`default_empty` > `ai` > `human`)
      Bir zonasi ko'rilmagan rasta HAR DOIM «ko'rilmagani uchun bo'sh»
      bo'lib ko'rinardi — hatto ikkinchi kamera uni ISHONCH bilan bo'sh
      deb ko'rgan bo'lsa ham. RAD ETILDI: u MONOTON EMAS — ko'rilmagan
      zonasi bor kameraning QO'SHILISHI to'liq tasdiqlangan rastani
      «hech kim qaramagan» holatiga TUSHIRARDI, ya'ni kamera qo'shish
      o'lchovni yomonlashtirardi.

  «ENG KUCHLI DALIL YUTADI» (`human` > `ai` > `default_empty`)  ⟵ TANLANDI
      `default_empty` faqat SHU verdiktni bergan zonalarning BIRORTASIDA
      ham dalil bo'lmaganda qoladi. Ya'ni «ko'rilmagani uchun bo'sh»
      hisoblagichi AYNAN nazoratchining yo'qligi verdiktni belgilagan
      rastalarni sanaydi — bu esa direktor uchun ISH BAJARILADIGAN son
      (§C.10: «bu raqam katta bo'lsa nazoratchi ulgurmayapti»). Shu bilan
      birga D-15 ning «Nazoratchi tasdig'i bilan» kesishuvchi o'lchami
      ham saqlanadi: inson tasdig'i BOSHQA zona tufayli yo'qolmaydi.
=============================================================================
"""

_NO_COVERAGE: Final[str] = ResolutionSource.NO_COVERAGE.value
"""`no_coverage` — HAM verdikt, HAM manba, va ikkalasi JUFT (D-22).

`stall_slot_occupancy` da `CHECK ((verdict = 'no_coverage') =
(resolution_source = 'no_coverage'))` aynan shu juftlikni majburlaydi
(05-05, deviatsiya #7), ya'ni bu funksiya sxema bilan bitta gapni
aytadi.
"""


def _rank(table: tuple[str, ...], value: str, *, kind: str) -> int:
    """`value` ning `table` dagi o'rni — noma'lum qiymat OCHIQ rad etiladi.

    ⚠ `ValueError` NI YUTMAYDI VA UNI QAYTA YOZADI: xom `tuple.index()`
      xatosi «'x' is not in tuple» deb chiqardi va chaqiruvchi qaysi
      qiymat, qaysi ro'yxatda yo'qligini KO'RA OLMASDI. Domen funksiyasi
      noma'lum verdikt bilan JIMGINA ishlashi esa eng yomon variant:
      u tartibni tasodifiy tanlab, hisobotni jimgina buzardi.
    """
    try:
        return table.index(value)
    except ValueError:
        raise ValueError(
            f"aggregate_stall_slot(): noma'lum {kind}: {value!r}. "
            f"Ruxsat etilganlari: {list(table)}."
        ) from None


def effective_verdict(event_verdict: str, review_verdict: str | None) -> tuple[str, str]:
    """Bitta ZONANING yakuniy javobi va uning MANBAI — uch manbali hosila (§C.10).

    =======================================================================
    ⛔ AI-06 HISOBLANADI, YOZILMAYDI.

        review mavjud        -> (review_verdict,  'human')
        verdict = 'uncertain'-> ('empty',         'default_empty')
        aks holda            -> (event_verdict,   'ai')

    Ikkinchi shox — D-19 ning butun mexanizmi: kun oxirigacha
    tasdiqlanmagan `uncertain` «bo'sh» bo'ladi, LEKIN `zone_reviews` ga
    SOXTA qator YOZILMAYDI. Yozilsa tizim «nazoratchi buni bo'sh deb
    tasdiqladi» deb YOLG'ON gapirardi va o'sha yolg'on keyin trening
    datasetiga tushib, modelni O'ZINING xatosiga o'rgatardi.

    `resolution_source` — hisobotdagi «alohida belgi» ning O'ZI: usiz uch
    butunlay boshqa holat («model bo'sh dedi», «hech kim qaramadi»,
    «bu rastani birorta kamera ko'rmaydi») hisobotda BIR XIL ko'rinardi.
    =======================================================================

    ⚠ INSON JAVOBI `uncertain` HAM BO'LISHI MUMKIN («aniq ayta olmayman»,
      UI-SPEC §7.3) va u shunday QOLADI — jimgina «bo'sh» ga
      aylantirilmaydi. Farq o'lchanadigan: `default_empty` «hech kim
      qaramadi» degani, `('uncertain', 'human')` esa «QARADI va ayta
      olmadi» degani. Ikkalasini bir joyga yig'ish nazoratchining ishini
      uning yo'qligi bilan tenglashtirardi.

    Args:
        event_verdict: `occupancy_events.verdict` — AI ning javobi.
        review_verdict: `zone_reviews.human_verdict` yoki javob
            yozilmagan bo'lsa `None`. ⚠ NAVBAT TURI BO'YICHA FILTR YO'Q:
            D-15 bo'yicha ko'r audit javobi ham bandlikni TUZATADI.
            Filtr faqat ANIQLIK HISOBOTIDA bor
            (`app/services/accuracy_report.py`) va u boshqa savolga
            javob beradi.

    Returns:
        `(verdict, resolution_source)` — ikkalasi ham xom `str`
        (`StrEnum` a'zosi emas), chunki qiymat to'g'ridan-to'g'ri
        `stall_slot_occupancy` ustuniga boradi.

    Raises:
        ValueError: verdikt (AI niki yoki insonniki) uchta ruxsat
            etilgan qiymatdan biri bo'lmasa.
    """
    _rank(_VERDICT_PRIORITY, event_verdict, kind="AI verdikti")

    if review_verdict is not None:
        _rank(_VERDICT_PRIORITY, review_verdict, kind="inson verdikti")
        return review_verdict, ResolutionSource.HUMAN.value

    if event_verdict == OccupancyVerdict.UNCERTAIN.value:
        return OccupancyVerdict.EMPTY.value, ResolutionSource.DEFAULT_EMPTY.value

    return event_verdict, ResolutionSource.AI.value


def aggregate_stall_slot(zone_results: Sequence[tuple[str, str]]) -> tuple[str, str]:
    """Bir RASTANING bir SLOTDAGI javobi — kameralararo agregatsiya (AI-05).

    Ustuvorlik: `occupied > uncertain > empty > no_coverage`
    (modul docstringi). Tenglik `_SOURCE_STRENGTH` bilan buziladi.

    ⛔ BO'SH KIRISH `no_coverage` BERADI, `empty` EMAS. Bu D-22 ning
       yagona kodda ifodalangan joyi: rasta haqida MA'LUMOT YO'Q degani
       «rasta bo'sh» degani emas. Ikkalasini tenglashtirish kameralarni
       umuman ko'rmaydigan rastani hisobotda «hammasi joyida» qilib
       ko'rsatardi.

    ⚠ `default_empty` MANBALI ZONA `empty` SIFATIDA QATNASHADI — ya'ni u
      ustuvorlikda `empty` bo'lib turadi, manbasi esa YO'QOLMAYDI va
      g'olib bo'lganda chiqishga o'tadi.

    Args:
        zone_results: shu rastani shu slotda qamragan HAR bir zonaning
            `effective_verdict()` chiqishi. Bo'sh ketma-ketlik —
            qamrovsizlik (zonasi yo'q, yoki kadr yaroqsiz bo'lgani uchun
            hodisa yozilmagan; 05-08 ning ikkala sababi ham XATO EMAS).

    Returns:
        `(verdict, resolution_source)` — `stall_slot_occupancy` ning
        ikkala ustuni. Bo'sh kirishda `('no_coverage', 'no_coverage')`.

    Raises:
        ValueError: noma'lum verdikt/manba, yoki `default_empty` manbasi
            `empty` dan boshqa verdikt bilan kelgan bo'lsa — o'sha juftlik
            `effective_verdict()` dan CHIQMAYDI, ya'ni uning kelishi
            chaqiruvchida nosozlik borligini bildiradi.
    """
    if not zone_results:
        return _NO_COVERAGE, _NO_COVERAGE

    for verdict, source in zone_results:
        _rank(_VERDICT_PRIORITY, verdict, kind="zona verdikti")
        _rank(_SOURCE_STRENGTH, source, kind="zona manbai")
        if (
            source == ResolutionSource.DEFAULT_EMPTY.value
            and verdict != OccupancyVerdict.EMPTY.value
        ):
            raise ValueError(
                "aggregate_stall_slot(): `default_empty` manbasi FAQAT `empty` "
                f"verdikti bilan keladi (olindi: {verdict!r}). Bu juftlik "
                "`effective_verdict()` dan chiqmaydi."
            )

    winner_verdict = min(
        (verdict for verdict, _ in zone_results),
        key=lambda verdict: _rank(_VERDICT_PRIORITY, verdict, kind="zona verdikti"),
    )
    winner_source = min(
        (source for verdict, source in zone_results if verdict == winner_verdict),
        key=lambda source: _rank(_SOURCE_STRENGTH, source, kind="zona manbai"),
    )
    return winner_verdict, winner_source
