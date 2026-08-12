"""7-fazaning besh enumi — YOPIQLIK **TO'PLAM TENGLIGI** bilan o'lchanadi.

Bu fayl `tests/unit/test_enums.py` ning naqshini davom ettiradi, lekin
ATAYIN kuchliroq shaklda va sabab 6-fazada o'lchangan:

⛔ `len()` YOKI «har a'zo bor» DA'VOSI YETARLI EMAS.

`len(X) == 4` bitta a'zoni BOSHQASIGA almashtirganda yashil qoladi;
«`justified` a'zosi bor» esa BESHINCHI a'zo qo'shilganda yashil qoladi.
D-12 ning butun qiymati aynan BESHINCHI a'zo (`other` / `custom`)
qo'shilishining IMKONSIZLIGIDA — ya'ni darvoza IKKI YO'NALISHNI ham
qulflashi shart va buni faqat TO'PLAM TENGLIGI qiladi.

`tests/unit/test_enums.py` ga qo'shilgan reyestr testi (`test_every_enum_
is_registered_in_all`) bilan JUFTLIKDA ishlaydi: u yerda «enum umuman
ro'yxatga olinganmi», bu yerda esa «to'plami yopiqmi» o'lchanadi.
"""

from __future__ import annotations

from enum import StrEnum

import pytest
from sbozor_core.enums import (
    OutboxKind,
    OutboxRecipientKind,
    OutboxStatus,
    ReconciliationCaseStatus,
    ReconciliationSubjectKind,
)

NEW_ENUMS: tuple[type[StrEnum], ...] = (
    ReconciliationCaseStatus,
    ReconciliationSubjectKind,
    OutboxKind,
    OutboxRecipientKind,
    OutboxStatus,
)
"""Beshala yangi enum — pastdagi umumiy darvozalarning kirishi.

Ro'yxat LITERAL: `sbozor_core.enums` dan `StrEnum` merosxo'rlarini
introspeksiya bilan yig'ish bu faylni BUTUN modulga bog'lab qo'yardi va
6-fazaning enumlari 7-fazaning darvozasini qizartirardi.
"""

ESCAPE_HATCH_TOKENS: tuple[str, ...] = ("other", "custom", "unknown", "skipped")
"""«Erkin matnni qaytarib keltiradigan» a'zo nomlari — NOM ham, QIYMAT ham.

⛔ Ro'yxat NOM va QIYMAT ni ALOHIDA tekshiradi: `OTHER = "misc"` ham,
`MISC = "other"` ham bir xil eshikni ochardi — birinchisi kod tomondan,
ikkinchisi DB va hisobot tomondan.
"""

READ_RECEIPT_STEMS: tuple[str, ...] = ("o'qil", "ko'ril", "read", "seen")
"""Telegram TASDIQLAMAYDIGAN da'volarning o'zaklari (Pitfall 2).

Bot API ning `sendMessage` javobi — `Message` obyekti; yetkazilganlik yoki
ochilganlik kvitansiyasi UMUMAN yo'q. Ya'ni bu o'zaklardan biri
`OutboxStatus` ning hujjatiga tushishi «tizim isbotlab bo'lmaydigan da'vo
qilyapti» degani va u nizoda (D-02) aynan dalil sifatida o'qilardi.
"""


def _docstrings(enum_cls: type[StrEnum]) -> str:
    """Klass docstringi + a'zolarning O'Z docstringi (bo'lsa), bitta matnda.

    ⚠ NEGA IKKALASI: loyihaning enum uslubi a'zo ma'nosini KLASS
    docstringida yozadi (`AnomalyKind`, `ResolutionSource` naqshi), lekin
    kelajakdagi muallif a'zoga alohida docstring qo'shishi mumkin. Faqat
    bittasini o'qigan darvoza ikkinchisini KO'RMASDAN yashil qolardi —
    ya'ni taqiqni chetlab o'tishning arzon yo'li ochiq turardi.
    """
    parts = [enum_cls.__doc__ or ""]
    parts.extend(
        member.__doc__ or ""
        for member in enum_cls
        if member.__doc__ is not None and member.__doc__ != enum_cls.__doc__
    )
    return "\n".join(parts)


def test_case_status_is_a_closed_set_of_four() -> None:
    """`ReconciliationCaseStatus` — AYNAN shu to'rt qiymat (D-12).

    ⛔ TO'PLAM TENGLIGI, `len()` EMAS: `len(...) == 4` bitta a'zoni
    boshqasiga almashtirganda yashil qolardi va hisobot jimgina boshqa
    guruhlarni sanardi.
    """
    assert {member.value for member in ReconciliationCaseStatus} == {
        "new",
        "in_review",
        "justified",
        "unjustified",
    }


def test_case_status_has_no_escape_hatch() -> None:
    """⛔ BESHINCHI («erkin matn») A'ZO YO'Q — NOM ham, QIYMAT ham (D-12).

    Erkin matnni qaytarib keltiradigan a'zo hisobotda AMALDA eng katta
    guruh bo'lib qolardi va hit-rate (D-13) o'lchanmasdi: `justified /
    (justified + unjustified)` maxraji «bu qaysi guruhga kiradi?» savoliga
    javobsiz qatorlar bilan to'lardi.
    """
    names = {member.name.lower() for member in ReconciliationCaseStatus}
    values = {member.value.lower() for member in ReconciliationCaseStatus}

    for token in ESCAPE_HATCH_TOKENS:
        assert token not in names, (
            f"`ReconciliationCaseStatus` ga `{token}` NOMLI a'zo qo'shilgan — "
            "D-12 aynan shuni taqiqlaydi (erkin matn hisobotda guruhlanmaydi)."
        )
        assert token not in values, (
            f"`ReconciliationCaseStatus` da `{token}` QIYMATI bor — nom boshqacha "
            "bo'lsa ham DB va hisobot tomondan bu o'sha eshik."
        )


def test_subject_kind_is_a_closed_pair() -> None:
    """`ReconciliationSubjectKind` — AYNAN ikki a'zo (DQ-5).

    Uchinchi a'zo `subject_kind_matches_target` `CHECK` ini JIMGINA
    bo'shatardi: diskriminator qiymati bor, lekin unga mos ustun yo'q
    bo'lardi va `GROUP BY subject_kind` yolg'on guruh berardi.
    """
    assert {member.value for member in ReconciliationSubjectKind} == {
        "anomaly",
        "occupied_unpaid",
    }


def test_outbox_kind_is_a_closed_set() -> None:
    """`OutboxKind` — AYNAN to'rt xabar turi (BOT-04).

    To'plam yopiq, chunki matn `kind` + `payload` dan QURILADI (Pitfall 6):
    ro'yxatdan tashqari `kind` uchun quruvchi funksiya UMUMAN yo'q va u
    ish paytida `KeyError` bilan yiqilardi.
    """
    assert {member.value for member in OutboxKind} == {
        "payment_receipt",
        "overdue_reminder",
        "digest_morning",
        "digest_evening",
    }


def test_recipient_kind_is_a_closed_pair() -> None:
    """`OutboxRecipientKind` — AYNAN ikki qabul qiluvchi sinfi (D-26c).

    Uchinchi sinf `recipient_matches_vendor` `CHECK` ining ikki tomonlama
    tengligini buzardi: `vendor_id` na majburiy, na taqiqlangan bo'lgan
    qator paydo bo'lardi va manzil qaydan olinishi noaniq qolardi.
    """
    assert {member.value for member in OutboxRecipientKind} == {"vendor", "market_director"}


def test_outbox_status_is_a_closed_set() -> None:
    """`OutboxStatus` — holat mashinasining AYNAN besh holati (D-20).

    Oltinchi holat (`retrying`, `queued`, `unknown`) mashinani ikki xil
    o'qishga ochardi: `pending` allaqachon «urinish kutilmoqda» ni
    bildiradi va ikkinchi nom bilan bir xil holat ikki guruhda sanalardi.
    """
    assert {member.value for member in OutboxStatus} == {
        "pending",
        "sent",
        "delivered",
        "failed",
        "blocked",
    }


def test_outbox_status_documents_the_exact_meaning_of_delivered() -> None:
    """`delivered` ning ma'nosi KODDA so'z bilan yozilgan (Pitfall 2).

    ⚠ IJOBIY NAZORAT: pastdagi SALBIY da'vo (`..._do_not_promise_read_
    receipts`) yolg'iz o'zi bo'sh docstringda ham YASHIL bo'lardi. Ya'ni
    ikkalasi JUFTLIK: biri ma'no yozilganini talab qiladi, ikkinchisi
    ortiqcha va'da berilmaganini.
    """
    text = _docstrings(OutboxStatus).lower()

    assert "200" in text, (
        "`OutboxStatus` hujjatida `delivered` ning ANIQ ma'nosi (Telegram 200 "
        "qaytardi) yozilmagan — usiz keyingi o'quvchi uni «foydalanuvchi ko'rdi» "
        "deb o'qiydi (Pitfall 2)."
    )
    assert "message_id" in text, (
        "`delivered` ning ma'nosi `message_id` gacha aniqlashtirilmagan — "
        "«200 qaytdi» yolg'iz o'zi qaysi javob ekanini aytmaydi."
    )


def test_outbox_status_docstrings_do_not_promise_read_receipts() -> None:
    """⛔ SALBIY DA'VO: hujjat «o'qildi» / «ko'rildi» ni VA'DA QILMAYDI.

    =========================================================================
    Bu Pitfall 2 ning KOD TOMONDAGI QULFI.

    Telegram Bot API `sendMessage` uchun yetkazilganlik yoki ochilganlik
    kvitansiyasini UMUMAN bermaydi — javob faqat `Message` obyekti. Ya'ni
    hujjatga «foydalanuvchi o'qidi» ma'nosini yozish tizimni ISBOTLAB
    BO'LMAYDIGAN da'voga majburlardi va o'sha da'vo nizoda (D-02) aynan
    dalil sifatida o'qilardi — ya'ni eng qimmat joyda eng zaif gap.

    ⚠ DARVOZA HUJJATNI O'LCHAYDI, UI MATNINI EMAS. UI tomondagi jufti
    uchala locale ustidan alohida yuradi; ikkalasi bir-birini
    ALMASHTIRMAYDI: hujjat kodni o'qiydigan odamga, matn esa direktorga
    gapiradi.
    =========================================================================
    """
    text = _docstrings(OutboxStatus).lower()

    for stem in READ_RECEIPT_STEMS:
        assert stem not in text, (
            f"`OutboxStatus` hujjatida `{stem}` o'zagi bor — Telegram "
            "yetkazilganlik/ochilganlik kvitansiyasini BERMAYDI va bu da'vo "
            "nizoda isbotlanmasdi (Pitfall 2)."
        )


@pytest.mark.parametrize("enum_cls", NEW_ENUMS, ids=lambda cls: cls.__name__)
def test_every_new_enum_is_a_str_enum(enum_cls: type[StrEnum]) -> None:
    """Beshalasi ham `StrEnum` — SQL parametri sifatida konversiyasiz ketadi.

    Oddiy `Enum` bo'lganda `f"{member}"` -> `"OutboxStatus.PENDING"` bo'lardi
    va o'sha qiymat JIMGINA `CHECK` ni buzib DB xatosiga aylanardi (yoki
    yomonrog'i: `text` ustunga tushib hisobotda ko'rinmas guruh yaratardi).
    """
    assert issubclass(enum_cls, StrEnum)

    for member in enum_cls:
        assert isinstance(member, str)
        assert f"{member}" == member.value
