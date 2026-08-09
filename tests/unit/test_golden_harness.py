"""Oltin to'plam mashinasi — MAVJUD, BO'SH VA UYG'ONISHGA TAYYOR (W0-9).

=============================================================================
BU FAYL ANIQLIKNI O'LCHAMAYDI VA O'LCHAY OLMAYDI HAM.

D-01: haqiqat (real Karmana kadrlari) hali yo'q, ya'ni modelning band/bo'sh
qarori to'g'riligini solishtiradigan narsa yo'q. Shuning uchun bu yerdagi
testlar MASHINANI o'lchaydi:

  * manifest sxemasi yaroqlimi va validator HAQIQATAN rad etadimi;
  * uyg'onish sharti skript MATNIDA bormi;
  * darvoza BUGUN uxlab yotibdimi.

⛔ «Sintetik yozuvlar ustidan aniqlik hisoblab, uni yashil deb ko'rsatish»
   BU YERDA TAQIQLANGAN va bu `05-VALIDATION.md` ning ochilish bandi:
   mexanika qatlamining yashilligi bilan aniqlik qatlamining yo'qligini
   yopish mumkin emas. Bu loyiha bu shaklni ikki marta rad etgan.

⚠ SKRIPT MATN SIFATIDA O'QILADI (§S-10). Uyg'onish sharti importdan
  KO'RINMAYDI: `run_gate` ni chaqirib «bugun darvoza qo'yilmadi» ni
  ko'rish shartning O'ZI to'g'ri yozilganini isbotlamaydi — shart butunlay
  olib tashlangan skript ham AYNAN shunday xulq qilardi (bugun karmana
  yozuvlari nol, ya'ni ikkala holatda ham darvoza qo'yilmaydi). Shuning
  uchun shart MANBA MATNIDAN qidiriladi.

  Manifest esa TESKARISI: uni skriptning O'Z validatori bilan o'qish
  SHART. Test JSON tekshiruvini qayta yozsa, ikkalasi birga xato bo'lganda
  baribir yashil qolardi (`karmana_seed.py` T-02-166 bilan bir xil qoida).
=============================================================================
"""

from __future__ import annotations

import importlib.util
import re
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any, Final, cast

import pytest

pytestmark = pytest.mark.golden

REPO_ROOT: Final = Path(__file__).resolve().parents[2]
SCRIPT_PATH: Final = REPO_ROOT / "scripts" / "eval-golden-set.py"
MANIFEST_PATH: Final = REPO_ROOT / "tests" / "fixtures" / "golden_set" / "manifest.jsonl"

MIN_SYNTHETIC_ROWS: Final = 6
"""Sintetik yozuvlarning QUYI CHEGARASI — `test_runtime_deps.py:291-302` naqshi.

Bo'sh (yoki deyarli bo'sh) manifestda quyidagi HAMMA assert jimgina o'tib
ketardi: nol yozuvda «hammasi synthetic» ham, «ikkala verdikt ham bor» ham
vakuum-rost bo'lardi. Chegara aynan shu yolg'on-yashilni yopadi.
"""

# ⚠ NAQSH `def` LARNI QIDIRADI, «wilson» so'zini EMAS. Skript o'z
#   docstringida matematikaning QAYERDA yashashini tushuntiradi va o'sha
#   tushuntirish darvozani qizartirmasligi kerak — aks holda yagona
#   «tuzatish» yo'li SABABNI O'CHIRISH bo'lardi (3-fazada o'lchangan).
DUPLICATED_MATH_PATTERN: Final = re.compile(r"^\s*def (wilson|confusion)", re.MULTILINE)


def _load_script() -> ModuleType:
    """Skriptni YO'L bo'yicha yuklaydi — nomida defis bor, ya'ni oddiy import ishlamaydi.

    `scripts/eval-golden-set.py` CLI sifatida chaqiriladi (`python
    scripts/eval-golden-set.py`), shuning uchun nomi paket qoidalariga
    bo'ysunmaydi va `import` bilan olinmaydi. `spec_from_file_location`
    ayni shu holat uchun.
    """
    spec = importlib.util.spec_from_file_location("eval_golden_set", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None, (
        f"skript yuklanmadi: {SCRIPT_PATH} — darvoza noto'g'ri faylni ko'rsatyapti"
    )
    module = importlib.util.module_from_spec(spec)
    # ⚠ `sys.modules` GA RO'YXATDAN O'TKAZISH MAJBURIY va sabab o'lchangan:
    #   skriptda `from __future__ import annotations` bor, ya'ni `@dataclass`
    #   annotatsiyalarni SATR sifatida ko'radi va ularni yechish uchun
    #   `sys.modules[cls.__module__].__dict__` ga murojaat qiladi. Modul
    #   ro'yxatda bo'lmasa u `None` qaytadi va yuklash
    #   `AttributeError: 'NoneType' object has no attribute '__dict__'`
    #   bilan yiqiladi — xato skriptda emas, YUKLOVCHIDA bo'lardi va
    #   sababi butunlay boshqa joyni ko'rsatardi.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def script() -> ModuleType:
    return _load_script()


@pytest.fixture(scope="module")
def script_source() -> str:
    return SCRIPT_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def rows(script: ModuleType) -> list[Any]:
    """Manifest — SKRIPTNING O'Z validatori bilan o'qilgan.

    Test o'zining parallel o'quvchisini yozmaydi: o'shanda validator
    buzilganda ham test yashil qolardi.
    """
    load_manifest = cast("Callable[[Path], list[Any]]", script.load_manifest)
    return load_manifest(MANIFEST_PATH)


def test_manifest_is_schema_valid_and_above_the_lower_bound(rows: list[Any]) -> None:
    """Manifest yaroqli, yetarlicha yozuvli va IKKALA verdikt ham bor.

    Ikkala verdiktning bo'lishi shart: faqat `occupied` yozuvlardan iborat
    to'plam «har doim band» deb javob beradigan soxta modelni 100% aniq
    ko'rsatardi (`05-RESEARCH.md` §C.8.4 ning bazaviy ulush ogohlantirishi).
    """
    assert len(rows) >= MIN_SYNTHETIC_ROWS, (
        f"manifestda {len(rows)} yozuv, kamida {MIN_SYNTHETIC_ROWS} kutilgan — "
        "kichik to'plamda quyidagi assertlar jimgina o'tib ketardi."
    )

    verdicts = {row.true_verdict for row in rows}
    assert verdicts == {"occupied", "empty"}, (
        f"manifestda faqat {sorted(verdicts)} verdikti bor. Ikkala tomon ham "
        "bo'lishi shart — bir tomonlama to'plamda doimiy javob beradigan soxta "
        "model mukammal ko'rinardi."
    )

    # ⚠ DA'VO FAQAT SINTETIK YOZUVLARGA TEGISHLI va bu farq muhim.
    #   Boshida bu assert BUTUN manifestga qo'yilgan edi va sabotaj uni
    #   ochib berdi: `karmana` qatori qo'shilgan zahoti u
    #   «o'zini-o'zi tasdiqlash tuzog'i» deb QIZARARDI — holbuki nazoratchi
    #   yorliqlagan real qator aynan KUTILGAN narsa. Xato xabar noto'g'ri
    #   joyni ko'rsatib, uyg'onish signalini ko'mib yuborardi.
    synthetic_labelers = {row.labeled_by for row in rows if row.source == "synthetic"}
    assert synthetic_labelers == {"geometry"}, (
        f"sintetik yozuvlarni `{sorted(synthetic_labelers)}` yorliqlagan. Sintetik "
        'yorliq FAQAT geometriyadan olinadi (`labeled_by = "geometry"`) — '
        "detektorning javobidan olinsa o'zini-o'zi tasdiqlash tuzog'i qaytadi."
    )

    # TESKARI YO'NALISH: real kadr HECH QACHON «geometry» tomonidan
    # yorliqlanmaydi. Sintetik kadrda geometriya haqiqatning O'ZI; real
    # kadrda esa haqiqat faqat INSONDAN keladi (D-01), va u yerda
    # «geometry» yozuvi yorliqning qayerdan kelganini yashirardi.
    karmana_labelers = {row.labeled_by for row in rows if row.source == "karmana"}
    assert "geometry" not in karmana_labelers, (
        '`karmana` yozuvi `labeled_by = "geometry"` bilan kelgan — real '
        "kadrning haqiqati faqat NAZORATCHIDAN keladi. Geometriya real "
        "kadrda quti borligini BILMAYDI."
    )


def test_manifest_validator_rejects_an_unknown_key(script: ModuleType, tmp_path: Path) -> None:
    """NAZORAT HOLATI: noma'lum kalit JIMGINA o'tkazib yuborilmaydi.

    ⚠ USIZ YUQORIDAGI TEST HECH NIMANI ISBOTLAMASDI. «Tushunmagan satrni
      tashlab ketadigan» validator ham AYNAN o'sha yashil natijani berardi —
      va o'sha validator bilan xato yozilgan `karmana` satrlari jimgina
      yo'qolardi, darvoza esa hech qachon uyg'onmasdi.
    """
    load_manifest = cast("Callable[[Path], list[Any]]", script.load_manifest)
    bad = tmp_path / "manifest.jsonl"
    bad.write_text(
        '{"image_ref": "x", "polygon": [[0.1, 0.1], [0.9, 0.1], [0.5, 0.9]], '
        '"true_verdict": "empty", "source": "synthetic", "labeled_by": "geometry", '
        '"labeled_at": "2026-08-08", "confidence": 0.99}\n',
        encoding="utf-8",
    )

    with pytest.raises(SystemExit) as error:
        load_manifest(bad)
    assert "confidence" in str(error.value), (
        f"rad etish sababi noma'lum kalitni nomlamadi: {error.value}"
    )


def test_manifest_validator_rejects_an_empty_manifest(script: ModuleType, tmp_path: Path) -> None:
    """NAZORAT HOLATI: bo'sh manifest ham XATO, «0 ta yozuv o'tdi» emas.

    Bo'sh to'plamda har qanday darvoza vakuum-rost bo'ladi — va aynan shu
    holat «darvoza bor» degan yolg'on ishonchni beradi.
    """
    load_manifest = cast("Callable[[Path], list[Any]]", script.load_manifest)
    empty = tmp_path / "manifest.jsonl"
    empty.write_text("\n", encoding="utf-8")

    with pytest.raises(SystemExit):
        load_manifest(empty)


def test_the_accuracy_gate_is_asleep_today(rows: list[Any]) -> None:
    """Darvoza BUGUN uxlab yotibdi — va bu KUTILGAN holat, OCHIQ aytiladi.

    ⚠ BU TEST «hozircha o'tkazib yuboramiz» degan skip EMAS. U bugungi
      holatni FAKT sifatida qayd etadi: `karmana` yozuvlari aynan nol.
      Real kadrlar qo'shilgan kuni bu test QIZARADI va o'sha qizil —
      SIGNAL: «oltin to'plam to'ldi, darvoza qurollandi, endi bu testni
      uyg'ongan holatga moslang».

      Skip qilinganda o'sha kun hech qanday signal bermasdi va darvoza
      jimgina, hech kim bilmagan holda ishga tushardi (yoki tushmasdi).
    """
    karmana = [row for row in rows if row.source == "karmana"]

    # ⚠ IKKI DA'VO ATAYIN AJRATILGAN. Boshida ular bitta
    #   `len(synthetic) == len(rows)` sharti bilan qo'shilgan edi va sabotaj
    #   buni ochib berdi: `karmana` qatori qo'shilganda u «noma'lum manba
    #   bor: ['karmana', 'synthetic']» deb qizarardi — ya'ni RUXSAT ETILGAN
    #   manbani noma'lum deb atardi. Bir shartga ikki savolni yuklash xato
    #   xabarini YOLG'ON qiladi.
    unknown_sources = {row.source for row in rows} - {"synthetic", "karmana"}
    assert not unknown_sources, (
        f"manifestda noma'lum manba: {sorted(unknown_sources)}. Ruxsat "
        "etilganlari — `synthetic` va `karmana`."
    )

    assert len(karmana) == 0, (
        f"manifestda {len(karmana)} ta `karmana` yozuvi paydo bo'ldi — DARVOZA "
        "UYG'ONDI.\n"
        "Bu XATO EMAS, bu KUTILGAN O'TISH. Endi bajarilishi kerak:\n"
        "  1. `python scripts/eval-golden-set.py` ni verdikt provayderi bilan "
        "ishga tushiring (05-12 uni ulaydi);\n"
        "  2. `MIN_N` va `THRESHOLD` qiymatlarini real ma'lumot asosida ATAYIN "
        "tasdiqlang;\n"
        "  3. bu testni uyg'ongan holatga moslang — va aniqlik da'vosini "
        "faqat O'LCHOVDAN keyin yozing."
    )


def test_script_text_declares_the_wake_condition(script_source: str) -> None:
    """Uyg'onish sharti skript MATNIDA — ya'ni kod o'zgarmasdan qurollanadi.

    Uchala bo'lak ham qidiriladi: shart bo'lmasa darvoza hech qachon
    uyg'onmasdi; `MIN_N` bo'lmasa u har qanday kichik namunada ham
    qurollanardi; `THRESHOLD` bo'lmasa u hech qachon YIQILMASDI.
    """
    assert 'source == "karmana"' in script_source, (
        'skriptda `source == "karmana"` shoxi topilmadi — darvoza real '
        "ma'lumot kelganda O'ZI uyg'onmaydi, ya'ni W0-9 ning butun va'dasi "
        "(«kodsiz uyg'onadi») bajarilmaydi."
    )
    for constant in ("MIN_N", "THRESHOLD"):
        assert re.search(rf"^{constant}: Final", script_source, re.MULTILINE), (
            f"`{constant}` skriptda modul darajasidagi nomlangan konstanta "
            "sifatida e'lon qilinmagan. Qiymat shart ichiga literal yozilsa, "
            "uni o'zgartirish darvozani JIMGINA bo'shatardi."
        )


def test_script_does_not_duplicate_the_statistics(script_source: str) -> None:
    """Matematika IMPORT QILINADI, takrorlanmaydi.

    Chalkashlik matritsasi va Wilson oralig'i `app/services/accuracy_report.py`
    da yashaydi (05-12). Ikki nusxa matematika ikki xil raqam berardi va
    hisobotga qaysi biri tushgani aniqlanmasdi — «94%» degan raqamning
    qaysi hisobdan chiqqani esa aynan nizo paytida so'raladi.
    """
    duplicated = DUPLICATED_MATH_PATTERN.search(script_source)
    found = duplicated.group(0).strip() if duplicated else ""
    assert duplicated is None, (
        f"skript statistikani O'ZI hisoblayapti: {found!r}. "
        "U `app/services/accuracy_report.py` dan import qilinishi shart."
    )
    assert "app.services.accuracy_report" in script_source, (
        "matematikaning import nuqtasi yo'q — 05-12 modulni yozganda uni "
        "skriptga ulash uchun joy qolmasdi va o'shanda hisob skriptning "
        "ichida ikkinchi marta yozilardi."
    )


# ===========================================================================
# 05-12 — MATEMATIKANING IMPORT NUQTASI ENDI HAQIQATAN YECHILADI
# ===========================================================================


def test_the_accuracy_module_import_point_resolves(script: ModuleType) -> None:
    """⚠ 05-01 DA BU SATR FAQAT MATN EDI — ENDI U HAQIQIY BOG'.

    `ACCURACY_MODULE` va `LOWER_BOUND_ATTR` 05-01 da yozilgan, lekin
    modul o'shanda MAVJUD EMAS edi: ular tekshirilmagan satrlar bo'lib
    turardi va `test_script_does_not_duplicate_the_statistics` faqat
    ularning MATNDA borligini o'lchardi.

    05-12 modulni yozdi, ya'ni endi import nuqtasining O'ZI
    o'lchanadigan bo'ldi: nom, atribut VA imzo. Nomdagi bitta xato
    (`accuracy_reports`) darvoza uyg'ongan kunigacha ko'rinmasdi.
    """
    module_name = cast("str", script.ACCURACY_MODULE)
    attribute = cast("str", script.LOWER_BOUND_ATTR)

    accuracy_module = importlib.import_module(module_name)
    lower_bound = getattr(accuracy_module, attribute, None)

    assert callable(lower_bound), (
        f"`{module_name}.{attribute}` chaqiriluvchi emas — skriptning import nuqtasi uzilgan"
    )
    assert lower_bound(90, 100) == pytest.approx(0.8256, abs=1e-3), (
        "import nuqtasi BOSHQA funksiyaga ulangan: `(to'g'ri, jami) -> Wilson quyi chegarasi` "
        "imzosi bajarilmadi"
    )


def test_the_armed_gate_runs_end_to_end_with_an_injected_provider(
    script: ModuleType, tmp_path: Path
) -> None:
    """⛔⛔ QUROLLANGAN YO'L BUGUN, SINTETIK MANIFEST BILAN TO'LIQ YURITILADI.

    =========================================================================
    NEGA BU KERAK: bugungacha `run_gate` ning QUROLLANGAN shoxi BIRORTA
    testda ishga tushmagan edi — `karmana` yozuvlari nol, ya'ni skript
    HAR DOIM birinchi shoxdan qaytardi. Ya'ni darvoza uyg'ongan kuni
    ishlaydimi degan savolga javob YO'Q edi va nosozlik AYNAN o'sha kuni,
    real ma'lumot kelganda ko'rinardi.

    Test HAQIQIY manifestga TEGMAYDI (`tmp_path` da o'zining sintetik
    nusxasini quradi), ya'ni `test_the_accuracy_gate_is_asleep_today`
    hamon uxlab yotgan holatni o'lchaydi.

    ⚠ PROVAYDER IN'EKTSIYA QILINADI — bu D-02 ning choki (`VerdictProvider`).
      Mahsulotda uning o'rniga `cv-service` ning `zone_verdict` yo'li
      keladi; bu yerda esa ATAYIN oddiy chaqiriluvchi, chunki o'lchanayotgan
      narsa DARVOZA, model EMAS.
    =========================================================================
    """
    run_gate = cast("Callable[..., int]", script.run_gate)
    load_manifest = cast("Callable[[Path], list[Any]]", script.load_manifest)

    manifest = tmp_path / "karmana.jsonl"
    manifest.write_text(_synthetic_karmana_manifest(), encoding="utf-8")
    rows = load_manifest(manifest)
    karmana = [row for row in rows if row.source == "karmana"]
    assert len(karmana) == 10, "nazorat: sintetik manifest kutilgan hajmda emas"

    # 10 dan 9 tasi to'g'ri -> Wilson quyi chegarasi ≈ 0,596 (QO'LDA:
    # p = 0,9; n = 10; maxraj = 1,38416; markaz = 0,84025;
    # yarim = 1,96·√(0,009 + 0,0096016)/1,38416 = 0,19318).
    def always_occupied(_image_ref: str, _polygon: tuple[tuple[float, float], ...]) -> str:
        """«Har doim band» deydigan SOXTA model — §C.8.4 ning aynan misoli."""
        return "occupied"

    passed = run_gate(rows, min_n=10, threshold=0.50, provider=always_occupied)
    failed = run_gate(rows, min_n=10, threshold=0.95, provider=always_occupied)

    assert passed == 0, "qurollangan darvoza o'tishi kerak bo'lgan holatda YIQILDI"
    assert failed == 1, "qurollangan darvoza yiqilishi kerak bo'lgan holatda O'TDI"


def test_the_armed_gate_refuses_to_run_without_a_provider(
    script: ModuleType, tmp_path: Path
) -> None:
    """⛔ Real ma'lumot keldi-yu provayder yo'q -> BALAND ovozda yiqiladi.

    ⚠ NAZORAT HOLATI: usiz yuqoridagi test «darvoza ishlaydi» degan
      da'voni yolg'iz ko'tarardi. Bu yerdagi shox esa «real ma'lumot
      keldi, lekin hech nima o'lchanmadi» degan JIMGINA nosozlikni
      yopadi va xabar provayderni QAYERDAN olishni nomma-nom aytadi.
    """
    run_gate = cast("Callable[..., int]", script.run_gate)
    load_manifest = cast("Callable[[Path], list[Any]]", script.load_manifest)

    manifest = tmp_path / "karmana.jsonl"
    manifest.write_text(_synthetic_karmana_manifest(), encoding="utf-8")

    with pytest.raises(SystemExit) as error:
        run_gate(load_manifest(manifest), min_n=10, threshold=0.85, provider=None)

    assert "cv-service" in str(error.value), (
        f"xabar provayderning manbasini nomlamadi: {error.value}"
    )


def _synthetic_karmana_manifest() -> str:
    """10 ta `karmana` yozuvi — 9 tasi `occupied`, 1 tasi `empty`.

    ⚠ NISBAT ATAYIN NOSIMMETRIK: «har doim band» deydigan provayder
      aynan 9/10 oladi, ya'ni yuqoridagi test ikki chegarani (0,50 va
      0,95) ajrata oladi. Teng nisbatda ikkala chegara ham bir tomonga
      tushib, test faqat BITTA shoxni o'lchardi.

    ⚠ `labeled_by` — `inspector`, `geometry` EMAS: real kadrning
      haqiqati faqat INSONDAN keladi va manifest validatori buni
      `test_manifest_is_schema_valid_and_above_the_lower_bound` da
      talab qiladi.
    """
    polygon = "[[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]]"
    lines = [
        f'{{"image_ref": "karmana/{index}.jpg", "polygon": {polygon}, '
        f'"true_verdict": "{"empty" if index == 0 else "occupied"}", '
        '"source": "karmana", "labeled_by": "inspector", "labeled_at": "2026-10-01"}'
        for index in range(10)
    ]
    return "\n".join(lines) + "\n"
