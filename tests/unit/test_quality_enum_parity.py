"""Sof modul konstantalari <-> `sbozor_core` enumlari — KO'PRIK TESTI.

=============================================================================
BU TEST 04-04 QOLDIRGAN QARZNI YOPADI VA U REJADA ATAYIN NOMLANGAN.

`app/services/quality.py` `sbozor_core.enums` ga ATAYIN BOG'LANMAGAN: sof
funksiya chegaralarni ham, domen enumlarini ham bilmasligi kerak va
o'sha ikki modul bir to'lqinda yozilgan edi (04-04 va 04-03 parallel).
Natijada ikkita mustaqil haqiqat manbai paydo bo'ldi:

    quality.py            ->  VERDICT_OK / VERDICT_DARK / VERDICT_BLANK / VERDICT_CORRUPT
    sbozor_core.enums     ->  SnapshotQuality.OK / DARK / BLANK / CORRUPT
    0014_snapshot_domain  ->  CHECK (quality_verdict IN (...))   <- enumdan HOSILA

Birinchi ikkisi bir kun ajralib ketsa nosozlik JIMGINA va KECH ko'rinardi:
`analyze()` yangi verdikt qaytarardi, `snapshot_repo.record()` esa uni
bazaga yozishga urinib `quality_verdict_allowed` CHECK'ida yiqilardi — va
bu FAQAT ISH PAYTIDA, birinchi o'sha turdagi kadrda, ya'ni ehtimol
ertalabki 06:00 slotida sodir bo'lardi. O'sha bir slot esa qaytarib
bo'lmaydigan dalil.

Uchinchi bo'g'in (CHECK ifodasi) enum'dan HOSILA qilingan
(`models/snapshot.py::SNAPSHOT_QUALITY_CHECK`) va u 04-03 da qulflangan.
Ya'ni zanjirning YAGONA qo'riqlanmagan bo'g'ini — birinchisi bilan
ikkinchisi orasidagi, va u aynan shu fayl.
=============================================================================

⚠ BU FAYL `test_quality_filter.py` NING O'RNINI BOSMAYDI. U yerda savol
  «qoida to'g'rimi?» (qaysi kadr `dark` bo'ladi), bu yerda esa «ikki
  ro'yxat bir xilmi?». Ularni birlashtirish mumkin emas:
  `SnapshotQuality` ga yangi a'zo qo'shish sifat filtrining birorta
  testini qizartirmaydi (o'lchandi — sabotaj natijasi 04-05 SUMMARY'sida).
"""

from __future__ import annotations

from app.services.quality import (
    LIGHT_DAY,
    LIGHT_IR_NIGHT,
    LIGHT_LOW_LIGHT,
    LIGHT_MODES,
    LIGHT_UNKNOWN,
    QUALITY_VERDICTS,
    VERDICT_BLANK,
    VERDICT_CORRUPT,
    VERDICT_DARK,
    VERDICT_OK,
)
from sbozor_core.enums import SnapshotLightMode, SnapshotQuality
from sbozor_core.models.snapshot import (
    SNAPSHOT_LIGHT_MODE_CHECK,
    SNAPSHOT_QUALITY_CHECK,
)


def test_verdict_constants_equal_the_snapshot_quality_enum() -> None:
    """⛔ ZANJIRNING BIRINCHI BO'G'INI: sof modul <-> enum.

    To'plamlar AYNAN teng bo'lishi shart — ichki-to'plam emas. Ikkala
    yo'nalish ham nosozlik:

      * enum'da ORTIQCHA a'zo -> `analyze()` uni hech qachon qaytarmaydi,
        ya'ni UI o'sha holat uchun ikonka va tarjima chizadi, hujayra esa
        hech qachon o'sha holatga tushmaydi (o'lik legenda yozuvi);
      * sof modulda ORTIQCHA konstanta -> `record()` bazada
        `quality_verdict_allowed` CHECK'ida yiqiladi va bu FAQAT ish
        paytida ko'rinadi.
    """
    assert {VERDICT_OK, VERDICT_DARK, VERDICT_BLANK, VERDICT_CORRUPT} == {
        member.value for member in SnapshotQuality
    }


def test_the_verdict_tuple_has_no_duplicates() -> None:
    """NAZORAT BANDI: yuqoridagi to'plam taqqoslashi DUBLIKATNI YASHIRADI.

    Agar kimdir `VERDICT_BLANK = "dark"` deb yozib qo'ysa, to'plam
    taqqoslashi `{ok, dark, corrupt}` ni `{ok, dark, blank, corrupt}` bilan
    solishtirib QIZARARDI — lekin `VERDICT_CORRUPT = "blank"` kabi
    ALMASHTIRISH holatida to'plamlar TENG qolardi. Uzunlik tekshiruvi esa
    tuple ichidagi har qanday dublikatni tutadi.
    """
    assert len(QUALITY_VERDICTS) == len(set(QUALITY_VERDICTS)) == len(SnapshotQuality)


def test_verdict_tuple_equals_the_enum_values() -> None:
    """`QUALITY_VERDICTS` — hosila to'plam, u ham enum bilan tekshiriladi.

    Konstantalar ALOHIDA tekshirilgan bo'lsa ham, tuple qo'lda yig'iladi
    (`quality.py` da to'rtta nom sanab yozilgan) va undan bittasini
    tushirib qoldirish mumkin. O'shanda konstantalar to'g'ri, hosila
    to'plam esa KAM bo'lardi.
    """
    assert set(QUALITY_VERDICTS) == {member.value for member in SnapshotQuality}


def test_light_mode_constants_equal_the_snapshot_light_mode_enum() -> None:
    """D-12: `light_mode` — `quality_verdict` ning DUBLIKATI EMAS, SUPERSET.

    Ikki savol boshqa: «ishlatsa bo'ladimi?» va «qanday yorug'likda
    olingan?». Shuning uchun ikkala ro'yxat ham MUSTAQIL ravishda
    qulflanadi — bittasini tekshirib ikkinchisini qoldirish 5- va
    8-fazalarning segmentatsiyasini jimgina buzardi.
    """
    assert {LIGHT_DAY, LIGHT_LOW_LIGHT, LIGHT_IR_NIGHT, LIGHT_UNKNOWN} == {
        member.value for member in SnapshotLightMode
    }
    assert set(LIGHT_MODES) == {member.value for member in SnapshotLightMode}
    assert len(LIGHT_MODES) == len(set(LIGHT_MODES)) == len(SnapshotLightMode)


def test_every_pure_constant_survives_the_database_check_expression() -> None:
    """⛔ ZANJIRNING UCHALA BO'G'INI BIR JOYDA — sof modul -> enum -> CHECK.

    Ikkinchi bo'g'in (enum -> CHECK) 04-03 da `pg_catalog` dan qulflangan,
    lekin u bu yerdagi birinchi bo'g'in bilan HECH QAYERDA
    uchrashtirilmagan edi. Bu test uchalasini bitta assertga yig'adi:
    `analyze()` qaytaradigan HAR BIR satr bazaga yozilishi mumkinligi
    ko'rinadigan bo'ladi.

    ⚠ Nima uchun ifoda MATN sifatida tekshiriladi: `SNAPSHOT_QUALITY_CHECK`
      — SQL literali (`quality_verdict IN ('ok', ...)`) va u migratsiyaga
      AYNAN shu ko'rinishda tushadi. Uni parse qilish ifodaning o'z
      shaklini takrorlashni talab qilardi; a'zolikni izlash esa xuddi shu
      da'voni ancha arzon o'lchaydi.
    """
    for verdict in QUALITY_VERDICTS:
        assert f"'{verdict}'" in SNAPSHOT_QUALITY_CHECK, (
            f"{verdict!r} `quality_verdict_allowed` CHECK ifodasida yo'q — bazaga yozib bo'lmaydi"
        )
    for mode in LIGHT_MODES:
        assert f"'{mode}'" in SNAPSHOT_LIGHT_MODE_CHECK, (
            f"{mode!r} `light_mode_allowed` CHECK ifodasida yo'q"
        )
