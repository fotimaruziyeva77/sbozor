"""Quiet hours va payload allowlisti — TO'LIQ LITERAL JADVAL (D-18, Pitfall 6/7).

=============================================================================
KUTILGAN NATIJA MAHSULOT FUNKSIYASIDAN OLINMAYDI — U JADVALDA YOZILGAN.

`test_aggregate_stall_slot.py` da o'rnatilgan qoida: funksiyani chaqirib
natijani «kutilgan» deb saqlash testni funksiyaning O'Z AKSIGA aylantirardi
— qoida qanday buzilsa ham ikkala tomon birga o'zgarardi va test yashil
qolardi.

Shuning uchun `QUIET_HOURS_TABLE` ning har bir qatori QO'LDA yozilgan va
har biri BITTA savolga javob beradi: «shu turdagi xabar shu devor-soatida,
shu oyna ostida YUBORILADIMI yoki KUTADIMI?»
=============================================================================

=============================================================================
⛔⛔ JADVALNING BIRINCHI QATORI — FAZANING ENG QIMMAT DA'VOSI (D-18).

    payment_receipt @ 22:30, oyna 21:00 -> 08:00  =>  YUBORILADI

Ya'ni sotuvchi soat 20:30 da to'lasa kvitansiya DARHOL ketadi, quiet oyna
ochilgan bo'lsa ham. Uni ertaga surish nizo modelini (D-02) buzardi: kassir
«yozdim» deydi, sotuvchida esa hech qanday tasdiq yo'q.

⚠ QATOR SABOTAJ BILAN O'LCHANDI: `NOTIFICATION_META["payment_receipt"].
  never_suppressed` `False` ga o'zgartirilganda AYNAN shu qator (va uning
  yarim tundagi jufti) qizaradi — natija `07-06-SUMMARY.md` da.
=============================================================================

⚠ OYNA CHEGARALARI YARIM YOPIQ: `start` ICHKARIDA, `end` TASHQARIDA.
  Jadvalda ikkala chegara ham ALOHIDA qator bilan qulflangan — aks holda
  «21:00 da yuboriladimi?» savoli implementatsiyaning tasodifiga qolardi.
"""

from __future__ import annotations

from datetime import time
from typing import Final

import pytest
from app.jobs.notification_meta import (
    DEFAULT_OVERDUE_DAYS,
    DEFAULT_QUIET_HOURS_END,
    DEFAULT_QUIET_HOURS_START,
    NEVER_SUPPRESSED_OUTBOX_KINDS,
    NOTIFICATION_META,
    OUTBOX_PAYLOAD_KEYS,
    is_suppressed_now,
    outbox_payload,
)
from sbozor_core.enums import OutboxKind, OutboxRecipientKind
from sbozor_core.models.notification import MarketNotificationSettings

SENT: Final = "yuboriladi"
WAITS: Final = "kutadi"

_NIGHT_START: Final = time(21, 0)
_NIGHT_END: Final = time(8, 0)
"""Standart oyna — YARIM TUNNI KESIB O'TADI (`start > end`).

⚠ Qiymatlar shu yerda LITERAL yozilgan, `DEFAULT_QUIET_HOURS_*` dan
IMPORT QILINMAGAN: jadval mahsulot standartining AKSI bo'lib qolmasligi
kerak. Ikkalasining TENGLIGI esa alohida testda o'lchanadi — shunda
standart o'zgarganda jadval jimgina emas, OCHIQ qizaradi.
"""

_DAY_START: Final = time(12, 0)
_DAY_END: Final = time(14, 0)
"""Yarim tunni KESIB O'TMAYDIGAN oyna (`start < end`) — ikkinchi shox.

Faqat bitta shakl bilan yozilgan jadval `start < end` shoxini umuman
o'lchamasdi: standart oyna kechasi, ya'ni implementatsiya `start > end`
shoxining o'zi bilan ham hamma qatorni o'tkazib yuborardi.
"""

_RECEIPT: Final = OutboxKind.PAYMENT_RECEIPT.value
_OVERDUE: Final = OutboxKind.OVERDUE_REMINDER.value
_MORNING: Final = OutboxKind.DIGEST_MORNING.value
_EVENING: Final = OutboxKind.DIGEST_EVENING.value


QUIET_HOURS_TABLE: Final[tuple[tuple[str, time, time, time, str], ...]] = (
    # --- ⛔ D-18: KVITANSIYA OYNA ICHIDA HAM KETADI ---
    (_RECEIPT, time(22, 30), _NIGHT_START, _NIGHT_END, SENT),
    (_RECEIPT, time(2, 0), _NIGHT_START, _NIGHT_END, SENT),
    # --- Eslatma esa AYNAN o'sha paytda KUTADI (farq faqat `kind` da) ---
    (_OVERDUE, time(22, 30), _NIGHT_START, _NIGHT_END, WAITS),
    # --- YARIM TUNNI KESIB O'TISH shoxi (`start > end`) ---
    (_OVERDUE, time(2, 0), _NIGHT_START, _NIGHT_END, WAITS),
    # --- Oynadan TASHQARIDA ---
    (_EVENING, time(20, 45), _NIGHT_START, _NIGHT_END, SENT),
    (_OVERDUE, time(9, 0), _NIGHT_START, _NIGHT_END, SENT),
    # --- CHEGARALAR: `start` ichkarida, `end` tashqarida ---
    (_OVERDUE, _NIGHT_START, _NIGHT_START, _NIGHT_END, WAITS),
    (_OVERDUE, _NIGHT_END, _NIGHT_START, _NIGHT_END, SENT),
    # --- YARIM TUNNI KESMAYDIGAN oyna (`start < end`) ---
    (_MORNING, time(13, 0), _DAY_START, _DAY_END, WAITS),
    (_MORNING, time(15, 0), _DAY_START, _DAY_END, SENT),
    (_MORNING, _DAY_START, _DAY_START, _DAY_END, WAITS),
    (_MORNING, _DAY_END, _DAY_START, _DAY_END, SENT),
    # --- BO'SH oyna (`start == end`) = «tinch soat YO'Q» ---
    (_OVERDUE, time(3, 0), _NIGHT_START, _NIGHT_START, SENT),
)
"""`(kind, devor-soati, oyna boshi, oyna oxiri) -> kutilgan natija`.

⚠ HAR BIR SHOX QAMRALGAN: `start > end`, `start < end`, `start == end`,
ikkala chegara va D-18 istisnosi. Bittasini olib tashlash implementatsiya
uchun eshik ochadi — masalan `start == end` qatorisiz «butun sutka tinch»
o'qishi jimgina o'tib ketardi va eslatma AMALDA o'chardi.
"""


@pytest.mark.parametrize(("kind", "moment", "start", "end", "expected"), QUIET_HOURS_TABLE)
def test_quiet_hours_table(kind: str, moment: time, start: time, end: time, expected: str) -> None:
    """Jadvalning har bir qatori — mustaqil da'vo (D-18, Pitfall 7)."""
    actual = WAITS if is_suppressed_now(kind, moment=moment, start=start, end=end) else SENT

    assert actual == expected, (
        f"`{kind}` @ {moment} (oyna {start}-{end}): kutilgani «{expected}», "
        f"olingani «{actual}». Kvitansiya uchun bu D-18 ning buzilishi — "
        "sotuvchi hozirgina to'lagan pulining tasdig'ini ERTAGA olardi."
    )


def test_the_quiet_hours_table_covers_every_case() -> None:
    """⛔ NAZORAT — `parametrize` JIMGINA bo'shab qolmasin.

    Bo'sh (yoki qisqargan) jadval bilan yuqoridagi test 0 marta ishlaydi
    va pytest buni NUQSON deb hisoblamaydi — ya'ni D-18 ning butun
    o'lchovi jimgina yo'qolardi. Bu 05-fazaning W-2 darsi: darvoza
    o'lchayotgan holatning MAVJUDLIGINI isbotlashi kerak.
    """
    assert len(QUIET_HOURS_TABLE) >= 6, f"jadval qisqargan: {len(QUIET_HOURS_TABLE)} qator"

    kinds = {row[0] for row in QUIET_HOURS_TABLE}
    assert kinds == set(NOTIFICATION_META), (
        f"jadval barcha turlarni qamramaydi: {sorted(kinds)} != {sorted(NOTIFICATION_META)}"
    )

    windows = {(row[2], row[3]) for row in QUIET_HOURS_TABLE}
    crossing = {(start, end) for start, end in windows if start > end}
    plain = {(start, end) for start, end in windows if start < end}
    empty = {(start, end) for start, end in windows if start == end}
    assert crossing and plain and empty, (
        "uchala oyna shakli (yarim tunni kesuvchi / kesmaydigan / bo'sh) "
        f"jadvalda bo'lishi SHART: kesuvchi={len(crossing)}, "
        f"kesmaydigan={len(plain)}, bo'sh={len(empty)}"
    )

    receipt_inside_quiet = [
        row for row in QUIET_HOURS_TABLE if row[0] == _RECEIPT and row[4] == SENT
    ]
    assert receipt_inside_quiet, (
        "⛔ jadvalda «kvitansiya quiet oyna ICHIDA yuboriladi» qatori YO'Q — "
        "D-18 ning yagona bajariladigan da'vosi shu qator"
    )


def test_never_suppressed_is_derived_from_meta() -> None:
    """⛔ D-18 bayrog'i REYESTRDAN HOSILA, qo'lda sanalgan ro'yxat EMAS.

    Ikki da'vo birga o'lchanadi:
      1. to'plam reyestrdan HISOBLANADI (hosila qoidasi);
      2. u BUGUN aynan `{"payment_receipt"}` (mahsulot qarori).

    Faqat ikkinchisini yozish hosilani NUSXAGA aylantirardi, faqat
    birinchisini yozish esa BO'SH ROST bo'lardi — reyestrdagi barcha
    bayroqlar `False` bo'lsa ham tenglik bajarilardi.
    """
    derived = {kind for kind, meta in NOTIFICATION_META.items() if meta.never_suppressed}

    assert derived == NEVER_SUPPRESSED_OUTBOX_KINDS, (
        "to'plam reyestrdan hosila emas — qo'lda yozilgan nusxa bugun to'g'ri "
        "qiymat berardi va ertaga jimgina ajralib ketardi (04-04 ning 6-sabotaji)"
    )
    assert frozenset({_RECEIPT}) == NEVER_SUPPRESSED_OUTBOX_KINDS, (
        f"to'xtatilmaydigan turlar to'plami o'zgardi: {sorted(NEVER_SUPPRESSED_OUTBOX_KINDS)}. "
        "Yangi tur qo'shish ONGLI qadam bo'lishi kerak: u quiet hours ni ham, "
        "throttling ni ham chetlab o'tadi."
    )


def test_payload_allowlist_rejects_unknown_key() -> None:
    """Ro'yxatdan tashqari kalit — `ValueError` («kodda xato, ma'lumot xatosi emas»).

    ⚠ CHEGARA YOZISH PAYTIDA: noma'lum kalit UI'da ko'rinmasdi, lekin
      bazaga yozilardi va u yerdan `pg_dump` -> restic -> tashqi bucketga
      chiqardi (Pitfall 6).
    """
    with pytest.raises(ValueError, match="ruxsat etilmagan payload"):
        outbox_payload(_RECEIPT, secret="x")

    # NAZORAT: ruxsat etilgan kalitlar O'TADI, ya'ni funksiya hamma narsani
    # rad etmaydi (aks holda yuqoridagi da'vo bo'sh rost bo'lardi).
    assert outbox_payload(_RECEIPT, amount_soum=15_000, stall_code="A-01") == {
        "amount_soum": 15_000,
        "stall_code": "A-01",
    }
    # `None` qiymat TASHLANADI (`_detail()` bilan bir xil qoida).
    assert outbox_payload(_RECEIPT, amount_soum=1, cashier_name=None) == {"amount_soum": 1}


def test_payload_allowlist_is_per_kind_not_a_union() -> None:
    """⛔ Chegara HAR TUR UCHUN ALOHIDA — birlashma bilan tekshirilmaydi.

    Birlashma bilan tekshirish `payment_receipt` ga dayjestning kalitini
    yozishga ruxsat berardi va matn quruvchisi o'sha kalitni umuman
    kutmasdi — xabar yarim bo'sh chiqardi, xato esa hech qayerda
    ko'rinmasdi.
    """
    assert "anomaly_count" in OUTBOX_PAYLOAD_KEYS, "birlashma test farazini tasdiqlamadi"
    with pytest.raises(ValueError, match="ruxsat etilmagan payload"):
        outbox_payload(_RECEIPT, anomaly_count=3)

    derived_union = {key for meta in NOTIFICATION_META.values() for key in meta.payload_keys}
    assert derived_union == OUTBOX_PAYLOAD_KEYS, "birlashma reyestrdan hosila emas"


def test_payload_allowlist_has_no_evidence_key() -> None:
    """⛔ D-03 ning PAYLOAD tomondagi qulfi — dalil-kadr kaliti YO'Q.

    G7-2 `notification_outbox` ning USTUN nomlarini `information_schema`
    dan o'qiydi, lekin `payload` — `jsonb`: kadr havolasi u yerga USTUN
    emas, KALIT bo'lib kirsa darvoza uni KO'RMASDI. Telegram serverlari
    esa O'zR data-rezidentlik chegarasidan TASHQARIDA va yuborilgan baytni
    QAYTARIB BO'LMAYDI.
    """
    forbidden = ("snapshot", "image", "url", "object_key", "photo", "evidence")
    matched = sorted(
        f"{kind}.{key}"
        for kind, meta in NOTIFICATION_META.items()
        for key in meta.payload_keys
        if any(token in key.lower() for token in forbidden)
    )

    assert matched == [], (
        f"`payload` allowlistida dalil o'zakli kalit(lar) bor: {matched}. "
        "Nomuvofiqlik xabarida dalil HAVOLA bo'lib boradi (veb yuzasiga, "
        "autentifikatsiya ostida) — BAYT bo'lib bormaydi (D-03)."
    )


def test_recipient_kind_of_every_entry_is_a_closed_enum_member() -> None:
    """Reyestrdagi `recipient_kind` — `OutboxRecipientKind` DAN, literal emas.

    ⚠ Literal qiymat `ck_notification_outbox_recipient_kind_allowed` ga
      urilardi va xato AYNAN yozish paytida, mahsulotda ko'rinardi.

    ⚠ IKKINCHI DA'VO — REYESTR TO'LIQ: `OutboxKind` ning har bir a'zosi
      yozuvga ega. Yozuvsiz a'zo `outbox_payload()` da `KeyError` berardi
      va u faqat o'sha tur birinchi marta navbatga qo'yilganda ko'rinardi.
    """
    allowed = {member.value for member in OutboxRecipientKind}
    for kind, meta in NOTIFICATION_META.items():
        assert meta.recipient_kind in allowed, f"`{kind}` yopiq to'plamdan tashqarida"
        assert meta.kind == kind, f"reyestr kaliti yozuv bilan mos emas: {kind} != {meta.kind}"

    assert set(NOTIFICATION_META) == {member.value for member in OutboxKind}, (
        f"reyestr `OutboxKind` bilan mos emas: {sorted(NOTIFICATION_META)} != "
        f"{sorted(member.value for member in OutboxKind)}"
    )


def test_defaults_match_the_schema_server_defaults() -> None:
    """[ASSUMED] A2/A3 — konstantalar sxemaning `server_default` i bilan TENG.

    ⛔ IKKI QATLAM, IKKI MUDDAT: sxema standarti xom SQL yo'lini qoplaydi,
       bu konstantalar esa sozlama qatori UMUMAN YO'Q bo'lgan bozorni
       (`COALESCE` ning ikkinchi argumenti). Ular ajralganda bir xil bozor
       ikki xil oyna olardi — qator qo'shilgunicha bitta, qo'shilgach
       boshqasi — va farq hech qayerda ko'rinmasdi.

    ⚠ SXEMA TOMONIDAGI QIYMAT MODELDAN O'QILADI, qo'lda ko'chirilmaydi.
    """
    columns = MarketNotificationSettings.__table__.columns

    assert str(columns["quiet_hours_start"].server_default.arg) == f"'{_NIGHT_START:%H:%M}'"
    assert str(columns["quiet_hours_end"].server_default.arg) == f"'{_NIGHT_END:%H:%M}'"
    assert str(columns["overdue_days"].server_default.arg) == str(DEFAULT_OVERDUE_DAYS)

    assert (DEFAULT_QUIET_HOURS_START, DEFAULT_QUIET_HOURS_END) == (_NIGHT_START, _NIGHT_END), (
        "mahsulot standarti jadvalning oynasidan ajralib ketdi — jadval endi "
        "mahsulot ishlatadigan oynani emas, eskisini o'lchayapti"
    )
    assert DEFAULT_QUIET_HOURS_START > DEFAULT_QUIET_HOURS_END, (
        "standart oyna endi yarim tunni KESMAYDI — `start > end` shoxi mahsulot "
        "yo'lidan chiqib ketdi va u faqat jadvalda qolgan bo'lardi"
    )
