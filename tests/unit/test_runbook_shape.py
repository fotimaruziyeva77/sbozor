"""GO-LIVE RUNBOOKNING SHAKL DARVOZASI (D-22, SC#4 ning 1-yarmi).

=============================================================================
NEGA BU DARVOZA BOR.

`ops/docs/go-live.md` — yagona hujjat bo'lib, uni **ishlab chiqarish
kunida, bosim ostida, ehtimol boshqa odam** o'qiydi. Shu sababdan uning
nuqsoni boshqa hujjatlarnikidan qimmatroq: natijasiz yozilgan band
(«…ni bajaring» deb aytib, nima chiqishi kerakligini aytmaydigan qator)
o'qiyotgan odamga **bajarildi** degan taassurot beradi, holbuki hech
kim natijani solishtirmagan bo'ladi. Nosozlik keyin, deploy'dan bir
necha soat o'tib, butunlay boshqa joyda ko'rinadi.

Odam o'qiganda bu farq ko'rinmaydi — matn ikkala holatda ham «tartibli»
ko'rinadi. Shuning uchun shakl mexanik qulflanadi.

=============================================================================
⛔ TANLANGAN MEXANIKA — VA U RUNBOOKNING O'ZIDA HAM AYNAN SHU.

Har bir fenced kod bloki (```) yopilgandan keyingi BIRINCHI bo'sh
bo'lmagan qator `**Kutilgan natija:**` bilan boshlanishi SHART. Qoida
runbookning kirish qismida LITERAL yozilgan, ya'ni hujjat va darvoza
bir xil narsani aytadi va keyingi tahrirchi mexanikani faylning o'zidan
o'qiy oladi.

Namuna manbai — `ops/scripts/verify-tunnel.sh` ning «Chiqish kodi: 0 —
…; 1 — …» sarlavhasi: buyruqning yonida uning natijasi turadi.

=============================================================================
SKANERNING IKKI QOIDASI (`tests/unit/test_compose_sim_env.py` da
o'rnatilgan naqsh, 08-05 va 08-08 da takrorlangan).

1. **QUYI CHEGARA MAJBURIY.** Yo'l eskirsa yoki fayl ko'chirilsa skaner
   BO'SH matn ustida ishlab, quyidagi da'volarning uchtasi (b, c, d)
   JIMGINA yashil bo'lardi — «taqiqlangan ibora 0 marta uchradi» bo'sh
   faylda ham ROST. Shuning uchun mavjudlik `autouse` fixture'da, ya'ni
   u BESHALA o'lchovdan OLDIN bajariladi; alohida test bo'lganda u
   yolg'iz qizarib, qolgan to'rt da'vo bo'sh-rost holida yashil bo'lib
   turardi.

2. **PREDIKATNING O'ZI NAZORAT NAMUNASI BILAN O'LCHANADI.** «Topilmadi»
   shaklidagi da'vo buzuq predikat bilan MANGU yashil bo'ladi. Shuning
   uchun (c) va (d) ning ikkalasi ham avval sintetik namunada
   TOPADI, keyin haqiqiy faylda TOPMASLIGINI talab qiladi.

⚠ Taqiqlangan iboralar SHU FAYLNING O'ZIDA bor va bu muammo emas:
  skaner `ops/docs/go-live.md` ni o'qiydi, o'zini emas (2-qoida,
  `test_compose_sim_env.py` dagi bilan bir xil sinf).

=============================================================================
⛔ SKANER `ops/docs/monitoring.md` GA QO'LLANMAYDI — VA BU ONGLI QAROR.

`monitoring.md` bu konvensiyadan OLDIN yozilgan va u boshqa janr:
sozlash yo'riqnomasi, deploy tartibi emas. Uni shu darvoza ostiga
kiritish 08-19 ning qamrovidan tashqaridagi faylni qayta yozishni
talab qilardi (SCOPE BOUNDARY). Band ochiq va u shu yerda nomlangan.
=============================================================================
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNBOOK = REPO_ROOT / "ops" / "docs" / "go-live.md"

EXPECTED_RESULT_MARKER = "**Kutilgan natija:**"
"""⛔ TANLANGAN MEXANIKA. Runbookning kirish qismida ham AYNAN shu satr."""

MIN_RUNBOOK_LINES = 200
"""Quyi chegara — 1-qoida.

Bugungi fayl ~519 qator. Chegara PASTKI: bo'lim qo'shilsa u qayta
ko'rib chiqilmaydi, fayl skeletga aylanib qolsa esa darhol qizaradi.
"""

MIN_COMMAND_BLOCKS = 12
"""Quyi chegara (c) uchun.

Bugungi faylda 28 blok. Nol blokli faylda «har blok juft» da'vosi
BO'SH-ROST bo'lardi — aynan shu chegara uni imkonsiz qiladi.
"""

MIN_FORBIDDEN_PHRASES = 3
"""Quyi chegara (d) uchun — rejaning talabi: kamida uch ibora o'lchansin.

Ro'yxat qisqarib ketsa «taqiqlangan ibora topilmadi» da'vosi
o'z-o'zidan rost bo'lib qolardi.
"""

REQUIRED_SECTION_MARKERS = (
    "deploy",
    "wireguard",
    "zaxira",
    "cutover",
    "rollback",
    "ro'yxat",
)
"""⛔ QAMROV, TO'PLAM TENGLIGI EMAS.

Yangi bo'lim qo'shilishi darvozani qizartirmaydi (runbook o'sishi
KERAK), mavjud mavzuning YO'QOLISHI esa qizartiradi. Teng to'plam
talabi har yangi bo'limda testni tahrirlashga majburlardi va u
sekin-asta «testni moslashtirish» odatini tug'dirardi.
"""

FORBIDDEN_PHRASES = (
    "tekshiring",
    "ko'ring",
    "e'tibor bering",
    "nazorat qiling",
    "kuzatib turing",
)
"""NATIJASIZ BUYRUQ BANDLARI.

Bu iboralar o'qiyotgan odamga ISH beradi, lekin BAJARILDI degan
javobni bermaydi: nimani ko'rgani, nima chiqishi kerakligi va noto'g'ri
natijada nima qilishi yozilmaydi. Runbookda ularning o'rniga buyruq
bloki va uning `**Kutilgan natija:**` juftligi turadi.
"""

RESTIC_PASSWORD_CLAUSE_MARKERS = (
    "RESTIC_PASSWORD",
    "serverdan tashqarida",
    "ikki joyda",
    "ikki odam",
)
"""(e) ning to'rt belgisi.

⛔ Faqat `RESTIC_PASSWORD` ning uchrashi YETARLI EMAS: kalit `.env`
tavsifida ham uchraydi. O'lchanadigan da'vo — SAQLASH BANDINING
mavjudligi, ya'ni parolning server tashqarisida, ikki joyda va ikki
odam bilan turishi (T-08-85).
"""


def _fence_line(line: str) -> bool:
    return line.strip().startswith("```")


def _unpaired_command_blocks(text: str) -> list[tuple[int, str]]:
    """`**Kutilgan natija:**` bilan JUFTLANMAGAN kod bloklari.

    Natija: `(blok ochilgan qator raqami, blokdan keyingi birinchi
    bo'sh bo'lmagan qator)` juftliklari. Qator raqami 1 dan boshlanadi —
    xabar to'g'ridan-to'g'ri tahrirlanadigan joyni ko'rsatishi uchun.
    """
    lines = text.splitlines()
    unpaired: list[tuple[int, str]] = []
    opened_at: int | None = None

    for index, line in enumerate(lines):
        if not _fence_line(line):
            continue
        if opened_at is None:
            opened_at = index
            continue

        after = index + 1
        while after < len(lines) and not lines[after].strip():
            after += 1
        following = lines[after].strip() if after < len(lines) else "<fayl tugadi>"
        if not following.startswith(EXPECTED_RESULT_MARKER):
            unpaired.append((opened_at + 1, following[:80]))
        opened_at = None

    return unpaired


def _count_command_blocks(text: str) -> int:
    return sum(1 for line in text.splitlines() if _fence_line(line)) // 2


def _resultless_hits(text: str) -> list[tuple[int, str]]:
    """Natijasiz buyruq iboralarining uchrashuvlari — qator raqami bilan.

    ⚠ `\\b` ISHLATILMAYDI: o'zbek lotinidagi apostrof (`ko'ring`) `\\w`
      emas, ya'ni `\\b` so'z chegarasini ibora O'RTASIDA topardi. Shakl
      shuning uchun aniq: ibora oldidan ham, keyinidan ham harf/raqam/
      apostrof KELMASLIGI kerak — bu `ko'rinadi` va `tekshiriladi` kabi
      TO'G'RI so'zlarni tutmaydi.
    """
    hits: list[tuple[int, str]] = []
    patterns = [
        (phrase, re.compile(rf"(?<![\w']){re.escape(phrase)}(?![\w'])", re.IGNORECASE))
        for phrase in FORBIDDEN_PHRASES
    ]
    for index, line in enumerate(text.splitlines(), start=1):
        for phrase, pattern in patterns:
            if pattern.search(line):
                hits.append((index, phrase))
    return hits


@pytest.fixture(autouse=True)
def _scanner_actually_reads_the_runbook() -> None:
    """QUYI CHEGARA — BESHALA o'lchovdan OLDIN (1-qoida).

    Fayl yo'q bo'lsa (b), (c) va (d) BO'SH matn ustida jimgina yashil
    bo'lardi. Bu fixture ularni bir xil, aniq sabab bilan qizartiradi.
    """
    assert RUNBOOK.is_file(), (
        f"`{RUNBOOK.relative_to(REPO_ROOT).as_posix()}` topilmadi — go-live runbooki "
        "ko'chirilgan yoki o'chirilgan. Bu darvozaning qolgan da'volari bo'sh matn "
        "ustida hech nimani isbotlamaydi."
    )


def test_the_runbook_exists_and_is_not_a_skeleton() -> None:
    """(a) Fayl bor va u SKELET emas."""
    lines = RUNBOOK.read_text(encoding="utf-8").splitlines()

    assert len(lines) >= MIN_RUNBOOK_LINES, (
        f"`ops/docs/go-live.md` da atigi {len(lines)} qator bor, kamida "
        f"{MIN_RUNBOOK_LINES} kutilgan. Deploy tartibi, zaxira tasdig'i, cutover va "
        "rollback bandlari bitta faylga sig'ishi kerak — bu uzunlikda ularning "
        "biri yo'qolgan."
    )

    header = lines[0]
    for requirement in ("FOUND-07", "SC#4"):
        assert requirement in header, (
            f"runbook sarlavhasida `{requirement}` yo'q: {header!r}. Talab ID'lari "
            "sarlavhada turadi (`ops/docs/monitoring.md` naqshi) — usiz hujjat qaysi "
            "mezonni yopayotganini hech kim ayta olmaydi."
        )


def test_every_required_section_is_present() -> None:
    """(b) Majburiy mavzular QAMROVI — to'plam tengligi EMAS."""
    headings = [
        line.strip().lower()
        for line in RUNBOOK.read_text(encoding="utf-8").splitlines()
        if line.startswith("## ")
    ]

    # NAZORAT: sarlavhalar umuman o'qilmasa quyidagi tsikl bo'sh to'plamda
    # ishlab, HAR marker «yo'q» bo'lardi — ya'ni darvoza yolg'on-QIZIL
    # bo'lardi. Chegara uni sababi bilan ajratadi.
    assert len(headings) >= len(REQUIRED_SECTION_MARKERS), (
        f"runbookdan atigi {len(headings)} ta `## ` sarlavha o'qildi ({headings}) — "
        "sarlavha shakli o'zgargan bo'lsa bu darvoza ham yangilanishi kerak"
    )

    missing = [
        marker
        for marker in REQUIRED_SECTION_MARKERS
        if not any(marker in heading for heading in headings)
    ]

    assert not missing, (
        f"go-live runbookida MAJBURIY bo'lim(lar) yo'q: {missing}\n"
        f"Mavjud sarlavhalar: {headings}\n\n"
        "D-22 runbookning mazmunini nomma-nom sanaydi: deploy tartibi, WireGuard/"
        "CAM-02, birinchi zaxira va tiklash, cutover qoidasi, rollback yo'li va "
        "go-live oldi ro'yxati. Bo'lim qo'shish bu darvozani qizartirmaydi — "
        "YO'QOTISH qizartiradi."
    )


def test_every_command_block_is_paired_with_an_expected_result() -> None:
    """(c) ⛔ HAR buyruq bloki `**Kutilgan natija:**` bilan JUFT."""
    text = RUNBOOK.read_text(encoding="utf-8")

    blocks = _count_command_blocks(text)
    assert blocks >= MIN_COMMAND_BLOCKS, (
        f"runbookda atigi {blocks} ta kod bloki topildi, kamida {MIN_COMMAND_BLOCKS} "
        "kutilgan. Bloklarsiz bu o'lchov BO'SH-ROST bo'lardi: juftlanmagan blok "
        "topilmasligi uchun blokning O'ZI bo'lmasligi yetarli."
    )

    # ⛔ NAZORAT NAMUNASI (2-qoida): predikat AVVAL sintetik matnda
    #    TOPADI. Usiz buzuq parser (masalan fence'ni tanimay qolgan)
    #    haqiqiy faylda ham hech nima topmasdi va darvoza MANGU yashil
    #    bo'lardi.
    control = "```bash\nls\n```\n\nOddiy matn, marker yo'q.\n"
    control_hits = _unpaired_command_blocks(control)
    assert len(control_hits) == 1, (
        f"nazorat namunasida juftlanmagan blok TOPILMADI ({control_hits}) — "
        "parser buzuq, ya'ni quyidagi da'vo hech nimani o'lchamaydi"
    )

    unpaired = _unpaired_command_blocks(text)
    assert not unpaired, (
        "go-live runbookida KUTILGAN NATIJASIZ buyruq bloki bor "
        f"(qator -> blokdan keyingi matn): {unpaired}\n\n"
        f"Har blokdan keyingi birinchi bo'sh bo'lmagan qator `{EXPECTED_RESULT_MARKER}` "
        "bilan boshlanishi SHART. Natijasiz buyruq operatorga ish beradi, lekin "
        "«bajarildimi?» savoliga javob bermaydi — nosozlik keyin, butunlay boshqa "
        "joyda ko'rinadi."
    )


def test_no_resultless_directive_phrases() -> None:
    """(d) ⛔ Natijasiz buyruq iboralari faylda 0 marta."""
    assert len(FORBIDDEN_PHRASES) >= MIN_FORBIDDEN_PHRASES, (
        f"taqiqlangan iboralar ro'yxati {len(FORBIDDEN_PHRASES)} a'zoli, kamida "
        f"{MIN_FORBIDDEN_PHRASES} kutilgan — qisqargan ro'yxat bilan quyidagi "
        "da'vo o'z-o'zidan rost bo'lardi"
    )

    # ⛔ NAZORAT NAMUNASI (2-qoida): detektor AVVAL topishi kerak.
    control = f"1. Jurnalni {FORBIDDEN_PHRASES[0]}.\n"
    assert _resultless_hits(control), (
        "nazorat namunasida taqiqlangan ibora TOPILMADI — regex buzuq va quyidagi "
        "«0 marta» da'vosi bo'sh-rost"
    )

    # NAZORAT-2: to'g'ri so'zlar TUTILMAYDI. Usiz darvoza `tekshiriladi`
    # kabi butunlay o'rinli so'zlarni ham qizartirib, keyingi muallifni
    # matnni buzishga majburlardi.
    assert not _resultless_hits("Versiya tengligi deploy kunida tekshiriladi va ko'rinadi."), (
        "regex so'z ICHIDAN moslashdi — `tekshiriladi`/`ko'rinadi` taqiqlanmagan"
    )

    hits = _resultless_hits(RUNBOOK.read_text(encoding="utf-8"))
    assert not hits, (
        f"go-live runbookida NATIJASIZ buyruq ibora(lar)i bor (qator, ibora): {hits}\n\n"
        "Ular buyruq bloki va uning kutilgan natijasi bilan almashtiriladi: operator "
        "nima yugurtirishini, nima chiqishi kerakligini va boshqa natijada nima "
        "qilishini bir joyda o'qiydi."
    )


def test_the_restic_password_off_server_clause_exists() -> None:
    """(e) `RESTIC_PASSWORD` ning off-server saqlash bandi MAVJUD (T-08-85)."""
    text = RUNBOOK.read_text(encoding="utf-8")

    missing = [marker for marker in RESTIC_PASSWORD_CLAUSE_MARKERS if marker not in text]

    assert not missing, (
        f"go-live runbookida `RESTIC_PASSWORD` ning saqlash bandi TO'LIQ EMAS — "
        f"yetishmayotgan belgi(lar): {missing}\n\n"
        "restic repo'si HAR DOIM shifrlangan va parolni tiklash yo'li YO'Q. Parol "
        "faqat VPS ning `.env` ida qolsa, VPS o'limi zaxirani ham o'ldiradi va buni "
        "FAQAT falokat kuni bilib olinadi (T-08-85). Shuning uchun band uch narsani "
        "birga aytishi kerak: parol serverdan tashqarida, ikki joyda va ikki odam "
        "biladi — imzo joyi esa `08-HUMAN-UAT.md` da."
    )
