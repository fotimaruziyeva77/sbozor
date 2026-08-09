"""SOXTA DETEKTOR YO'LINI YOPADIGAN DARVOZA — §S-14 ning statik yarmi.

=============================================================================
NEGA BU DARVOZA BOR: 03-14 VA 04-12 NOSOZLIKLARINING UCHINCHI TAKRORI.

Ikkala fazada ham «qulaylik uchun» qo'yilgan soxta amalga oshirilish
butun bir yo'lni O'LCHANMAGAN qoldirgan edi, va ikkalasida ham testlar
YASHIL turgan — nosozlikni konteyner ko'rsatgan, test emas.

Aniqlash yo'lida bu xavf eng katta: `onnxruntime` sekin, artefakt og'ir
va CI'da yo'q — ya'ni «tez ishlaydigan soxta detektor» yozish uchun
bosim ENG YUQORI. Bu darvoza o'sha yo'lni yopadi.

=============================================================================
⚠ DARVOZA RO'YXAT EMAS, PREDIKAT (`test_sentry_processes.py` naqshi).

U «`FakeDetectorSession` bormi?» deb SO'RAMAYDI — bunday ro'yxat n+1 chi
nomda jimgina eskirardi. U `app/**` daraxtini AST bilan skanerlab
so'raydi:

    «`InferenceSession` ni chaqiradigan joylar soni AYNAN BITTAMI?»
    «Taqiqlangan prefiksli klass bormi?»

Noma'lum ikkinchi amalga oshirilish topilsa — `pytest.fail`, `skip`
EMAS. «O'tkazib yuborish» shoxi ATAYIN yo'q: aynan o'sha shox 04-12 ning
darvozasini jimgina bo'shatgan edi.

=============================================================================
⚠⚠ SKANER AST BILAN YURADI, MATN BO'YICHA EMAS — VA BU ATAYIN.

`ast.parse` + `ClassDef`/`Call` tugunlari. Shunda izohlar va
docstringlar tekshiruv maydoniga UMUMAN kirmaydi, ya'ni:

  (a) bu faylning O'ZI taqiqlangan nomlarni ochiq yozishi mumkin
      (yuqoridagi `FakeDetectorSession` kabi) va darvoza o'zini o'zi
      qizartira olmaydi — 03-07 da o'lchangan muammoning yechimi;
  (b) `app/**` dagi izohda «soxta detektor yozilmaydi» deb yozish
      YOLG'ON-QIZIL bermaydi, ya'ni darvozani bo'shatish bosimi
      tug'ilmaydi.
=============================================================================
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Final

import pytest

APP_ROOT: Final = Path(__file__).resolve().parents[2] / "app"

SESSION_FACTORY: Final = "InferenceSession"
"""`onnxruntime` sessiyasini quradigan yagona chaqiruv nomi."""

FORBIDDEN_CLASS_PREFIXES: Final[tuple[str, ...]] = ("Fake", "Stub", "Dummy", "Mock")
"""Soxta amalga oshirilishning odatiy nomlanish shakllari.

⚠ Bu prefikslar `app/**` da UMUMAN taqiqlangan — faqat detektor uchun
  emas. Sabab: «soxta ombor klienti» yoki «soxta broker» ham aynan shu
  sinfdagi nosozlikni beradi, va ular 05-08 da tug'iladi.
"""

MIN_SCANNED_MODULES: Final = 5
"""QUYI CHEGARA: bo'sh daraxtda «topilmadi» da'volari JIMGINA yashil bo'lardi.

⚠ Usiz bu faylning butun mantig'i `APP_ROOT` yo'li eskirgan kunda
  o'z-o'zidan o'chib qolardi — nol fayl skanerlansa, nol qoidabuzarlik
  topiladi va darvoza abadiy yashil bo'lardi.
"""


def _module_paths() -> list[Path]:
    """`app/**` daraxtidagi barcha Python modullari."""
    return sorted(APP_ROOT.rglob("*.py"))


def _parse(path: Path) -> ast.Module:
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as error:  # pragma: no cover - sintaksis xatosi CI'da lint bilan ushlanadi
        pytest.fail(f"`{path}` AST bilan o'qilmadi: {error}")


@pytest.fixture(scope="module")
def modules() -> list[tuple[Path, ast.Module]]:
    paths = _module_paths()
    assert len(paths) >= MIN_SCANNED_MODULES, (
        f"`{APP_ROOT}` da faqat {len(paths)} modul topildi, kamida "
        f"{MIN_SCANNED_MODULES} kutilgan — yo'l eskirgan bo'lsa quyidagi "
        "da'volar bo'sh daraxt ustida jimgina o'tib ketardi"
    )
    return [(path, _parse(path)) for path in paths]


def test_inference_session_is_constructed_in_exactly_one_place(
    modules: list[tuple[Path, ast.Module]],
) -> None:
    """`InferenceSession` chaqiruvi AYNAN BITTA joyda.

    Ikkinchi chaqiruv joyi ikki xil nosozlikning belgisi:
      - «test uchun yengil sessiya» — ya'ni soxta amalga oshirilish;
      - har kadrda yangi sessiya — ya'ni grafni qayta-qayta yuklash.

    Ikkalasi ham ISTISNO TASHLAMAYDI, shuning uchun ular faqat SANOQ
    bilan ushlanadi.
    """
    call_sites: list[str] = []
    for path, tree in modules:
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            target = node.func
            name = (
                target.attr
                if isinstance(target, ast.Attribute)
                else target.id
                if isinstance(target, ast.Name)
                else None
            )
            if name == SESSION_FACTORY:
                call_sites.append(f"{path.relative_to(APP_ROOT)}:{node.lineno}")

    assert len(call_sites) == 1, (
        f"`{SESSION_FACTORY}` {len(call_sites)} joyda chaqirilyapti: "
        f"{call_sites}. Kutilgani AYNAN BITTA — `detector/session.py` "
        "dagi `DetectorSession.__init__`. Ikkinchi joy yo soxta amalga "
        "oshirilish, yo har kadrda qayta yuklash."
    )


def test_no_faked_implementation_class_lives_in_the_app_tree(
    modules: list[tuple[Path, ast.Module]],
) -> None:
    """`Fake*`/`Stub*`/`Dummy*`/`Mock*` prefiksli klass `app/**` da YO'Q.

    ⚠ Bu tekshiruv ISHLAB CHIQARISH daraxtiga tegishli, testlarga emas:
      testlarda soxtalashtirish qonuniy vosita. Xavf — soxta narsaning
      `app/` ga KO'CHIB O'TISHI, chunki o'shanda u ishlab chiqarishda
      ham tanlanishi mumkin bo'lib qoladi.
    """
    offenders: list[str] = []
    for path, tree in modules:
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name.startswith(FORBIDDEN_CLASS_PREFIXES):
                offenders.append(f"{path.relative_to(APP_ROOT)}:{node.lineno} {node.name}")

    assert offenders == [], (
        f"`app/**` da soxta amalga oshirilish topildi: {offenders}. Soxta "
        "detektor butun inference yo'lini O'LCHANMAGAN qoldiradi (03-14 va "
        "04-12 nosozliklarining takrori). Soxtalashtirish TEST daraxtida "
        "yashaydi, ishlab chiqarishda emas."
    )


def test_the_single_call_site_is_the_detector_session(
    modules: list[tuple[Path, ast.Module]],
) -> None:
    """Yagona chaqiruv joyi AYNAN `detector/session.py` da.

    Sanoq yolg'iz yetmaydi: chaqiruv boshqa modulga KO'CHSA ham sanoq
    `1` bo'lib qolardi, egalik esa yo'qolardi (kim ochadi, kim yopadi
    degan savol javobsiz qolardi).
    """
    owners = {
        str(path.relative_to(APP_ROOT))
        for path, tree in modules
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == SESSION_FACTORY
    }

    assert owners == {str(Path("detector") / "session.py")}, (
        f"`{SESSION_FACTORY}` egasi kutilmagan modulda: {sorted(owners)}"
    )


def test_providers_are_named_explicitly_at_the_call_site(
    modules: list[tuple[Path, ast.Module]],
) -> None:
    """Sessiya `providers=` ni ATAYIN beradi — standartga tayanmaydi.

    `onnxruntime` provayderni o'zi tanlaganda, image'ga bir kun GPU
    provayderi kirib qolsa u JIMGINA tanlanardi va Contabo VPS'da
    (GPU'siz) nosozlik ish paytida ochilardi.

    ⚠ Tekshiruv AST orqali — argument HAQIQATAN berilganini o'lchaydi,
      izohda aytilganini emas.
    """
    calls = [
        node
        for _, tree in modules
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == SESSION_FACTORY
    ]
    assert calls, f"`{SESSION_FACTORY}` chaqiruvi topilmadi — yo'l eskirgan"

    for call in calls:
        keywords = {keyword.arg for keyword in call.keywords}
        assert "providers" in keywords, (
            f"`{SESSION_FACTORY}` `providers=` siz chaqirilyapti "
            f"(qator {call.lineno}) — standart tanlovga tayanish GPU "
            "provayderi kirib qolgan kunda jim nosozlik berardi."
        )


def test_the_resolution_is_read_from_the_graph_and_not_hard_coded() -> None:
    """Rezolyutsiya `get_inputs()[0].shape` dan O'QILADI.

    Qattiq yozilgan raqam eng yomon shakldagi nosozlikni berardi:
    noto'g'ri o'lchamdagi kirish tenzorida `onnxruntime` ISTISNO
    TASHLAMAYDI — u boshqacha natija qaytaradi, ya'ni aniqlik JIMGINA
    tushardi va nosozlik model sifatiga yozilardi.
    """
    source = (APP_ROOT / "detector" / "session.py").read_text(encoding="utf-8")

    assert "get_inputs()[0].shape" in source, (
        "rezolyutsiya grafdan o'qilmayapti — model varianti almashganda "
        "kod o'zgarishi kerak bo'lardi (§4.1)"
    )
