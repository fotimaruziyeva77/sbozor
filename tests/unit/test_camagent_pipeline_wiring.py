"""CamAgent marshruti kadrni BANDLIK QUVURIGA ulaydi — va TO'G'RI TARTIBDA.

=============================================================================
NEGA BU DARVOZA BOR.

`api/internal/camagent.py` ning O'Z docstringi marshrutning maqsadini
shunday yozgan: kadr `snapshots` ga tushmasa «zona chizib bo'lmaydi va
BANDLIK TAHLILI BOSHLANMAYDI. Bu marshrut o'sha bo'shliqni yopadi».

Amalda u va'daning YARMINI bajarardi: kadrni yozardi, tahlilga esa
UZATMAS edi. Karmana FAQAT shu yo'ldan ishlaydi, ya'ni uning HAMMA kadri
quvurni chetlab o'tardi. O'lchangan oqibat (2026-09-14, jonli bazada):

    occupancy_events        0 qator          — hech qachon
    stall_slot_occupancy    har qator `no_coverage`
    daily_charges           28-avgustdan beri BO'SH

Ya'ni bozorga pul yozilmay qolgan va buni hech bir test ko'rmagan,
chunki bu marshrut uchun darvoza UMUMAN YO'Q edi.

=============================================================================
⛔ TARTIB — SHU DARVOZANING ASOSIY DA'VOSI.

Ikki chaqiruvning O'RNI muzokara qilinmaydi va u `jobs/capture.py`
(server o'zi tortadigan yo'l) dan ko'chirilgan:

  * `seed_snapshot` — TRANZAKSIYA ICHIDA. Kadr qatori bilan urug'
    hodisasi birga yoziladi yoki ikkalasi ham yozilmaydi; aks holda
    hodisasiz qolgan kadrni keyin topishning yo'li yo'q.

  * `enqueue_detect` — TRANZAKSIYADAN KEYIN. Ichkarida bo'lsa Valkey
    uzilishi `COMMIT` ni yiqitardi va KADR ham yo'qolardi; bundan
    tashqari xabar `COMMIT` dan oldin chiqsa `cv-service` hali mavjud
    bo'lmagan `snapshots` qatorini izlab «ko'rinmadi» deb ketardi.

Shuning uchun test ikkalasining BORLIGINI emas, QAYERDA ekanini ham
o'lchaydi. «Bor» darajasidagi tekshiruv chaqiruvni tranzaksiya ichiga
ko'chirib qo'yishni o'tkazib yuborardi — va o'sha nosozlik faqat Valkey
uzilgan kuni ko'rinardi.

=============================================================================
⚠ BU DARVOZA NIMANI ISBOTLAMAYDI.

U MANBA STRUKTURASINI o'lchaydi, ish paytidagi xatti-harakatni emas.
Sabab: `_accept` kadr baytlarini S3'dan o'qiydi, ya'ni uchdan-uchgacha
sinov uchun obyekt xotira, jadval, kamera va NVR fiksturalari kerak.
Urug' mantig'ining O'ZI esa allaqachon o'lchangan —
`tests/integration/test_review_seed.py`. Bu yerdagi savol boshqa va u
aynan o'sha bo'shliq edi: «uni KIMDIR chaqiradimi?»
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Final

MANBA: Final = (
    Path(__file__).resolve().parents[2]
    / "services"
    / "core-api"
    / "app"
    / "api"
    / "internal"
    / "camagent.py"
)


def _modul() -> ast.Module:
    return ast.parse(MANBA.read_text(encoding="utf-8"), filename=str(MANBA))


def _funksiya(nom: str) -> ast.AsyncFunctionDef:
    for tugun in ast.walk(_modul()):
        if isinstance(tugun, ast.AsyncFunctionDef) and tugun.name == nom:
            return tugun
    raise AssertionError(f"`{nom}` funksiyasi `{MANBA.name}` da topilmadi")


def _chaqiruvlar(tugun: ast.AST) -> list[str]:
    """Tugun ICHIDAGI barcha chaqiruvlarning nomlari."""
    nomlar: list[str] = []
    for ichki in ast.walk(tugun):
        if isinstance(ichki, ast.Call):
            fn = ichki.func
            if isinstance(fn, ast.Name):
                nomlar.append(fn.id)
            elif isinstance(fn, ast.Attribute):
                nomlar.append(fn.attr)
    return nomlar


def test_urug_kadr_bilan_BIR_TRANZAKSIYADA_yoziladi() -> None:
    """`seed_snapshot` `_accept` ichida — ya'ni `session.begin()` ostida.

    `_accept` butunlay tranzaksiya ichida chaqiriladi, shuning uchun
    uning ichidagi har qanday yozuv kadr qatori bilan bir xil taqdirni
    ko'radi. Aynan shu kerak.
    """
    chaqiruvlar = _chaqiruvlar(_funksiya("_accept"))
    assert "seed_snapshot" in chaqiruvlar, (
        "`_accept` `seed_snapshot` ni chaqirmaydi — CamAgent kadrlari "
        "nazoratchi navbatiga TUSHMAYDI va bandlik hech qachon "
        "o'lchanmaydi. Aynan shu nosozlik `daily_charges` ni "
        "2026-08-28 da to'xtatgan edi."
    )


def test_CV_navbati_tranzaksiyadan_KEYIN() -> None:
    """`enqueue_detect` `session.begin()` blokidan TASHQARIDA.

    ⛔ Bu testning butun qiymati shu yerda: chaqiruv MAVJUD bo'lsa-yu,
       `async with` ichida tursa — darvoza baribir QIZARISHI kerak.
    """
    marshrut = _funksiya("accept_snapshot")

    bloklar = [t for t in marshrut.body if isinstance(t, ast.AsyncWith)]
    assert bloklar, (
        "`accept_snapshot` da `async with ... session.begin()` bloki "
        "topilmadi — funksiya qayta yozilgan bo'lsa bu testni ham qayta "
        "o'qib chiqing."
    )

    ichkarida = [n for blok in bloklar for n in _chaqiruvlar(blok)]
    assert "enqueue_detect" not in ichkarida, (
        "`enqueue_detect` TRANZAKSIYA ICHIDA chaqirilyapti. Ikki oqibat "
        "va ikkalasi ham o'lchangan: (a) Valkey uzilsa `COMMIT` yiqiladi "
        "va KADR ham yo'qoladi, holbuki obyekt S3 da; (b) xabar `COMMIT` "
        "dan oldin chiqsa `cv-service` hali yo'q `snapshots` qatorini "
        "izlab «ko'rinmadi» deb chiqib ketadi."
    )

    hammasi = _chaqiruvlar(marshrut)
    assert "enqueue_detect" in hammasi, (
        "`accept_snapshot` `enqueue_detect` ni umuman chaqirmaydi — "
        "CamAgent kadrlari CV navbatiga HECH QACHON tushmaydi."
    )


def test_ikkala_chaqiruv_ham_IMPORT_qilingan() -> None:
    """Import yo'qolsa `NameError` faqat HAQIQIY kadr kelganda chiqardi.

    ⚠ Bu ortiqcha tuyulishi mumkin, lekin emas: yuqoridagi ikki test
      AST'ni o'qiydi va u nomning QAYERDAN kelganini bilmaydi. Importsiz
      kod ham AST darajasida «chaqiruv bor» deb ko'rinadi.
    """
    modul = _modul()
    nomlar = {
        alias.name
        for tugun in ast.walk(modul)
        if isinstance(tugun, ast.ImportFrom)
        for alias in tugun.names
    }
    yoq = {"seed_snapshot", "enqueue_detect", "VERDICT_OK"} - nomlar
    assert not yoq, f"`{MANBA.name}` da import qilinmagan: {sorted(yoq)}"
