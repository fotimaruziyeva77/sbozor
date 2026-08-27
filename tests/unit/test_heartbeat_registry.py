"""D-17 — RO'YXATGA OLINMAGAN CRON JIMGINA O'LA OLMAYDI (07-14).

=============================================================================
⛔⛔ BU DARVOZANING MAVJUD BO'LISH SABABI BITTA JUMLADA.

Cron jadvali `import` PAYTIDA olinadi (`worker.py` ning planer bo'limi,
`LabelScheduleSource`), ya'ni `scheduler` konteyneri qayta ishga
tushirilmasa YANGI VAZIFA RO'YXATGA OLINMAYDI — job hech qachon
ishlamaydi va ⛔ HECH QANDAY XATO CHIQMAYDI.

Buni birorta test USHLAY OLMAYDI: testlar `broker` reyestrini
jarayonning O'ZIDA o'qiydi, prodda esa eski jarayon eski jadval bilan
ishlab turaveradi.

Yagona mexanik himoya — IKKI REYESTR:

    app/api/internal/self_check.py::EXPECTED_COMPONENTS   (`never_seen`)
    app/jobs/alerting.py::_platform_signals::watched      (`*_stale` alerti)

va ikkinchisidagi «`None` HAM ESKIRISH» qoidasi. Ya'ni yurak urishi
UMUMAN yozilmagan komponent alert ochadi.

`.planning/phases/06-billing-va-kassir/deferred-items.md` ning ⛔ 2-BANDI
aynan shu bandning unutilishi edi: `day_close` yurak urishi YOZILADI,
lekin uning YO'QLIGI hech qayerda ko'rinmasdi.
=============================================================================

=============================================================================
⛔⛔ DARVOZA NOMLAR RO'YXATIGA TAYANMAYDI — U HOSILA.

`test_sentry_processes.py` ning falsafasi (04-12 darsi): qo'lda yozilgan
nomlar ro'yxati BUGUN to'g'ri bo'lardi va ERTAGA jimgina eskirardi —
aynan o'zi oldini olmoqchi bo'lgan nosozlik sinfi.

Shuning uchun komponent nomlari `app/jobs/` katalogidan ⛔ AST BILAN
yig'iladi. Import qilingan modullar ro'yxati YOZILMAYDI: o'sha ro'yxat
ham qo'lda yuritilardi va yangi fayl unga tushmasdi. AST butun katalogni
ko'radi.

⚠⚠ VA U ANNOTATSIYA SHAKLIGA BOG'LIQ EMAS — BU O'LCHANGAN, TAXMIN
   QILINMAGAN. Ijro paytida topildi:

       app/jobs/outbox.py        OUTBOX_COMPONENT: Final[str] = "..."
       app/jobs/day_close.py     DAY_CLOSE_COMPONENT: str      = "..."   <- BOSHQA

`Final[str]` ni talab qiladigan yig'uvchi IKKITA komponentni (`day_close`,
`billing_close`) JIMGINA o'tkazib yuborardi va darvoza ular ustida MANGU
yashil bo'lardi. Shuning uchun shart NOMDA (`*_COMPONENT`) va QIYMATDA
(satr konstantasi), annotatsiyada EMAS.
=============================================================================

⚠ QUYI CHEGARA MAJBURIY (`MIN_COMPONENTS`) — 06-UI-SPEC §15.2 ning darsi:
  yo'l noto'g'ri yozilganda yoki katalog ko'chirilganda skaner BO'SH
  to'plam qaytaradi va HAR BIR da'vo bo'sh-rost bo'lib yashil qoladi.
"""

from __future__ import annotations

import ast
import pathlib
from typing import TYPE_CHECKING, Final

import pytest
from app.api.internal import self_check
from app.jobs import alerting

if TYPE_CHECKING:
    from collections.abc import Iterator

REPO_ROOT: Final = pathlib.Path(__file__).resolve().parents[2]
JOBS_DIR: Final = REPO_ROOT / "services" / "core-api" / "app" / "jobs"
SELF_CHECK_PATH: Final = (
    REPO_ROOT / "services" / "core-api" / "app" / "api" / "internal" / ("self_check.py")
)

COMPONENT_SUFFIX: Final = "_COMPONENT"
"""Yurak urishi komponentini e'lon qiladigan konstantaning NOM naqshi."""

MIN_COMPONENTS: Final = 10
"""Skaner topishi SHART bo'lgan eng kam komponent soni — QUYI CHEGARA.

⚠ QUYI CHEGARA, ANIQ SON EMAS: yangi job qo'shilganda sanoq o'sadi va bu
  fayl TEGILMAYDI. Faqat komponentning YO'QOLISHI darvozani qizartiradi
  va u ONGLI harakat bo'lishi kerak.

⛔⛔ SON DASTLAB 8 QO'YILGAN EDI VA U TESHIK BO'LARDI — BU IJRO PAYTIDA
   TOPILDI, KEYIN EMAS. `Final[str]` ni talab qiladigan (ya'ni NOTO'G'RI)
   yig'uvchi AYNAN 8 ta komponent topadi — `day_close` va `billing_close`
   `: str` bilan e'lon qilingan. Ya'ni `>= 8` sharti o'sha nosozlikni
   O'TKAZIB YUBORARDI va darvoza ikki komponent ustida MANGU yashil
   bo'lardi. Pastdagi `ANNOTATION_VARIANTS` — o'sha bo'shliqning IKKINCHI,
   nomlangan qulfi.
"""

ANNOTATION_VARIANTS: Final[frozenset[str]] = frozenset({"day_close", "billing_close"})
"""⛔ IJOBIY NAZORAT: `Final[str]` SIZ e'lon qilingan komponentlar.

    app/jobs/day_close.py      DAY_CLOSE_COMPONENT: str = "day_close"
    app/jobs/billing_close.py  BILLING_CLOSE_COMPONENT: str = "billing_close"

Ular yig'uvchining annotatsiyaga BOG'LIQ EMASLIGINI o'lchaydi va bu
da'voni `MIN_COMPONENTS` yolg'iz o'zi BAJARA OLMAYDI (yuqoridagi ⛔⛔).
⚠ Ro'yxat mahsulotdan IMPORT QILINMAYDI — nomlar shu yerda QAYTA
  yozilgan (05-13 darsi): import darvozani o'zi tekshirayotgan qiymatga
  bog'lardi.
"""

# ---------------------------------------------------------------------------
# NOMLANGAN ISTISNOLAR — har biri SABAB bilan va ro'yxatlar O'SISHI TAQIQ
# ---------------------------------------------------------------------------

EXPECTED_EXEMPT: Final[frozenset[str]] = frozenset({"day_close"})
"""`EXPECTED_COMPONENTS` ga ATAYIN qo'shilmagan komponent — AYNAN BITTA.

`day_close` — 5-faza merosi va uning `self_check.py` docstringida OCHIQ
yozilgan qarz: «uni yo'l-yo'lakay qo'shish 6-fazani 5-fazaning qarziga
bog'lardi». Qaror o'sha rejaniki bo'lib qoladi, lekin u endi ⛔ RO'YXATGA
OLINGAN qarz: bu to'plamning uzunligi assert qilinadi, ya'ni ikkinchi
«vaqtincha» istisno qo'shib bo'lmaydi.
"""

WATCHED_EXEMPT: Final[frozenset[str]] = frozenset({"day_close", "alert_sweep", "capture_tick"})
"""`watched` ga ATAYIN kirmagan komponentlar — AYNAN UCHTA, har biri sabab bilan.

⛔ `alert_sweep` — SUPURGINING O'ZI. Uni o'z `watched` ro'yxatiga qo'yish
   AYLANMA bo'lardi: o'lgan supurgi o'zining o'lgani haqida alert
   yoza olmaydi. Aynan shuning uchun uning eskirishini BOSHQA JARAYON —
   `/internal/self-check` (`core-api` konteyneri) — ko'radi
   (`self_check.py` ning 2-QOIDASI).

⛔ `capture_tick` — AYNI SABAB (u ham worker jarayonida) VA ikkinchisi:
   kadr olishning yo'qligi allaqachon BOZOR KESIMIDA, boyroq signallar
   bilan o'lchanadi (`_market_signals` -> `capture_missed` /
   `capture_stopped`). Yurak urishi bo'yicha ikkinchi alert o'sha
   qatorlarni TAKRORLARDI va D-22 ning «yolg'on/ortiqcha alert kanalni
   o'ldiradi» qoidasiga tushardi.

⛔ `day_close` — `EXPECTED_EXEMPT` bilan bir xil, 5-fazaning ochiq qarzi.

⚠⚠ REJA BU RO'YXATNI «AYNAN BITTA» (`day_close`) DEB YOZGAN EDI — HAQIQAT
   UCHTA CHIQDI va farq SUMMARY da chetlanish sifatida qayd etilgan.
   Sonni bir joyga qadash o'rniga ⛔ HAR ISTISNONING SABABI shu yerda
   yozildi va to'plamning UZUNLIGI assert qilindi: himoya «uchta» sonida
   emas, ro'yxatning O'SA OLMASLIGIDA.
"""


# ---------------------------------------------------------------------------
# YIG'UVCHILAR — hammasi AST, birortasi qo'lda yozilgan ro'yxat emas
# ---------------------------------------------------------------------------


def _module_level_assignments(tree: ast.Module) -> Iterator[tuple[str, ast.expr]]:
    """Modul darajasidagi `NOM = qiymat` va `NOM: annotatsiya = qiymat` juftliklari.

    ⚠ FUNKSIYA VA SINF ICHIGA KIRILMAYDI: `tree.body` bo'ylab YUZAKI
      yuriladi. Aks holda mahalliy o'zgaruvchi ham «konstanta» bo'lib
      ko'rinardi.
    """
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.value is not None:
                yield node.target.id, node.value
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    yield target.id, node.value


def _component_constants() -> dict[str, str]:
    """`app/jobs/**.py` dagi `*_COMPONENT` konstantalari — nom -> qiymat.

    ⛔ ANNOTATSIYA TEKSHIRILMAYDI (fayl docstringining ikkinchi bloki):
       `Final[str]` ham, yalang'och `str` ham, annotatsiyasiz e'lon ham
       bir xil qabul qilinadi. Shart NOMDA va QIYMATNING SATR
       KONSTANTASI ekanida.
    """
    found: dict[str, str] = {}
    for path in sorted(JOBS_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for name, value in _module_level_assignments(tree):
            if not name.endswith(COMPONENT_SUFFIX):
                continue
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                found[name] = value.value
    return found


def _watched_pairs() -> tuple[tuple[str, str], ...]:
    """`_platform_signals` ichidagi `watched` korteji — (komponent, alert kaliti).

    ⛔ MANBA — MAHSULOTNING O'Z KODI, qo'lda yozilgan nusxa emas. Kortej
       elementlari `(KONSTANTA, "kalit")` shaklida, ya'ni birinchi element
       NOM: u `alerting` modulining o'zidan yechiladi (`getattr`), chunki
       konstantalar o'sha yerga IMPORT QILINGAN. Nom o'chirilsa yoki
       literalga aylantirilsa bu yig'uvchi buni DARHOL ko'radi.
    """
    source = pathlib.Path(alerting.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=alerting.__file__)
    for node in ast.walk(tree):
        if not isinstance(node, ast.AsyncFunctionDef) or node.name != "_platform_signals":
            continue
        for inner in ast.walk(node):
            if not isinstance(inner, ast.Assign):
                continue
            targets = [t.id for t in inner.targets if isinstance(t, ast.Name)]
            if "watched" not in targets or not isinstance(inner.value, ast.Tuple):
                continue
            return tuple(_pair(element) for element in inner.value.elts)
    pytest.fail("`_platform_signals` ichida `watched` korteji topilmadi — yig'uvchi eskirgan")


def _pair(element: ast.expr) -> tuple[str, str]:
    """`(KOMPONENT_KONSTANTASI, "alert_kaliti")` juftligini yechadi."""
    assert isinstance(element, ast.Tuple) and len(element.elts) == 2, (
        "`watched` elementi (komponent, kalit) juftligi emas"
    )
    component, key = element.elts
    assert isinstance(component, ast.Name), (
        "`watched` da komponent nomi LITERAL yozilgan — u konstantadan import "
        "qilinishi shart, aks holda ikki nusxa jimgina ajralib ketardi"
    )
    assert isinstance(key, ast.Constant) and isinstance(key.value, str)
    resolved = getattr(alerting, component.id, None)
    assert isinstance(resolved, str), (
        f"`{component.id}` `alerting` modulida topilmadi — import o'chirilgan"
    )
    return resolved, key.value


def _unregistered(components: set[str], registry: set[str], exempt: frozenset[str]) -> list[str]:
    """PREDIKAT — reyestrga tushmagan, istisno ham qilinmagan komponentlar.

    ⛔ NOMLAR RO'YXATI EMAS, PREDIKAT (04-12 darsi): darvoza qaysi
       komponentlar borligini BILMAYDI, u faqat «har topilgani reyestrda
       bormi?» degan savolni beradi. Shuning uchun ertaga qo'shiladigan
       yangi job ham AVTOMATIK ravishda shu talab ostiga tushadi.
    """
    return sorted(components - registry - exempt)


# ---------------------------------------------------------------------------
# 1. Har job komponenti `EXPECTED_COMPONENTS` da
# ---------------------------------------------------------------------------


def test_every_job_component_is_expected() -> None:
    """`app/jobs/` topilgan HAR komponent `/internal/self-check` reyestrida.

    Aks holda job ishlab turardi, endpoint esa uni UMUMAN ko'rmasdi:
    yurak urishi yozilgan bo'lardi, «u yozilmayapti» degan savol esa hech
    kim tomonidan berilmasdi.
    """
    components = _component_constants()
    assert len(components) >= MIN_COMPONENTS, (
        f"`app/jobs/` dan atigi {len(components)} komponent topildi "
        f"(kutilgan >= {MIN_COMPONENTS}) — skaner BO'SH ishladi va quyidagi "
        "da'volarning hammasi bo'sh-rost bo'lib qolardi"
    )
    unseen = sorted(ANNOTATION_VARIANTS - set(components.values()))
    assert unseen == [], (
        f"`Final[str]` SIZ e'lon qilingan komponent(lar) topilmadi: {unseen}. "
        "Yig'uvchi annotatsiya shakliga bog'lanib qolgan va u shu ikkisini "
        "JIMGINA o'tkazib yuboradi — darvoza ular ustida mangu yashil bo'lardi"
    )

    missing = _unregistered(
        set(components.values()), set(self_check.EXPECTED_COMPONENTS), EXPECTED_EXEMPT
    )
    assert missing == [], (
        f"komponent(lar) `EXPECTED_COMPONENTS` da YO'Q: {missing}. Cron jadvali "
        "`import` paytida olinadi, ya'ni ro'yxatga olinmagan vazifa JIMGINA "
        "ishlamay qo'yadi va hech qanday xato chiqmaydi — `deferred-items.md` "
        "ning 2-bandi aynan shunday BITTA unutilgan komponent edi"
    )


def test_the_expected_exemption_list_cannot_grow() -> None:
    """Istisno ro'yxati AYNAN BITTA element — «vaqtincha» ikkinchisi qo'shilmaydi.

    ⚠ UZUNLIK ASSERT QILINADI, MAZMUN EMAS DEB O'YLAMANG: ikkalasi ham
      tekshiriladi. Faqat mazmun tekshirilganda ro'yxatga yangi nom
      qo'shish testni BUZMASDI (to'plam a'zoligi hamon rost bo'lardi).
    """
    assert sorted(EXPECTED_EXEMPT) == ["day_close"]
    assert len(EXPECTED_EXEMPT) == 1, (
        "reyestrdan chetda qoldirilgan ikkinchi komponent paydo bo'ldi — "
        "istisno «keyin qo'shamiz» qarziga aylanmoqda"
    )


# ---------------------------------------------------------------------------
# 2. Har job komponenti `watched` da (uchta NOMLANGAN istisno bilan)
# ---------------------------------------------------------------------------


def test_every_job_component_is_watched() -> None:
    """Topilgan HAR komponent `_platform_signals::watched` da — yo'qligi ALERT beradi.

    ⛔ `EXPECTED_COMPONENTS` YOLG'IZ O'ZI YETMAYDI: u faqat
       `/internal/self-check` ni so'ragan odamga ko'rinadi. `watched` esa
       hech kim so'ramaganda ham Telegram xabarini TUG'DIRADI — D-20 ning
       «alert on absence of a success signal» qoidasi.
    """
    components = _component_constants()
    watched = {component for component, _key in _watched_pairs()}
    assert len(watched) >= 3, "`watched` korteji bo'sh o'qildi — yig'uvchi eskirgan"

    missing = _unregistered(set(components.values()), watched, WATCHED_EXEMPT)
    assert missing == [], (
        f"komponent(lar) `watched` da YO'Q: {missing}. Yurak urishining YO'QLIGI "
        "hech qanday alert bermasdi — job jimgina o'lardi (`deferred-items.md` 2-bandi)"
    )


def test_the_watched_exemption_list_cannot_grow() -> None:
    """Kuzatuvdan chetda qolganlar AYNAN UCHTA va har birining sababi kodda.

    ⚠ RO'YXAT REJADAGIDAN FARQ QILADI (reja «aynan bitta» degan) va bu
      farq YASHIRILMAGAN: `WATCHED_EXEMPT` docstringi uchala sababni ham
      yozadi. Himoya sonda emas — ro'yxatning O'SA OLMASLIGIDA.
    """
    assert sorted(WATCHED_EXEMPT) == ["alert_sweep", "capture_tick", "day_close"]
    assert len(WATCHED_EXEMPT) == 3, (
        "kuzatuvsiz qolgan to'rtinchi komponent paydo bo'ldi — uning sababi "
        "`WATCHED_EXEMPT` docstringida YOZILISHI shart"
    )


# ---------------------------------------------------------------------------
# 3. `watched` ning har kaliti `ALERT_META` da
# ---------------------------------------------------------------------------


def test_every_watched_key_has_alert_meta() -> None:
    """`watched` dagi HAR alert kaliti reyestrda — aks holda `_upsert()` YIQILARDI.

    `alerting._upsert()` `ALERT_META[key]` ni to'g'ridan-to'g'ri o'qiydi,
    ya'ni ro'yxatga olinmagan kalit ⛔ `KeyError` beradi. Supurgi esa uni
    `SQLAlchemyError` deb YUTMAYDI — butun yugurish yiqilardi va u bilan
    birga QOLGAN alertlar ham yo'qolardi.
    """
    keys = [key for _component, key in _watched_pairs()]
    assert keys, "`watched` bo'sh — yig'uvchi eskirgan"
    orphans = sorted(set(keys) - set(alerting.ALERT_META))
    assert orphans == [], (
        f"alert kalit(lar)i `ALERT_META` da YO'Q: {orphans} — `_upsert()` ular "
        "ustida `KeyError` bilan yiqilardi"
    )


# ---------------------------------------------------------------------------
# 4. NAZORAT — predikat HAQIQATAN ushlaydimi
# ---------------------------------------------------------------------------


def test_the_gate_catches_an_unregistered_component() -> None:
    """⛔ NAZORAT BANDI: sun'iy komponent bilan predikat YIQILISHI shart.

    =========================================================================
    ⛔ USIZ YUQORIDAGI UCHALA DA'VO HAM BO'SH-ROST BO'LARDI.

    Noto'g'ri yozilgan yig'uvchi (masalan `Final[str]` ni talab qiladigan
    variant — bu ijro paytida HAQIQATAN topilgan nosozlik) bo'sh yoki
    to'liqmas to'plam qaytaradi va `missing == []` MANGU yashil qoladi.
    Bu test predikatning O'ZINI o'lchaydi: reyestrda YO'Q nom berilganda u
    o'sha nomni QAYTARISHI shart.
    =========================================================================
    """
    synthetic = "zond_component_never_registered"
    caught = _unregistered(
        {synthetic, *self_check.EXPECTED_COMPONENTS},
        set(self_check.EXPECTED_COMPONENTS),
        EXPECTED_EXEMPT,
    )
    assert caught == [synthetic], (
        "predikat ro'yxatga OLINMAGAN komponentni ko'rmadi — darvoza mavjud "
        "bo'lib turib hech nimani o'lchamaydi"
    )

    # NAZORATNING IKKINCHI YARMI: istisno qilingan nom QAYTMASLIGI kerak,
    # aks holda predikat shunchaki «hamma narsani qaytaradigan» funksiya
    # bo'lardi va birinchi assert ham bo'sh-rost bo'lib qolardi.
    exempted = _unregistered({"day_close"}, set(self_check.EXPECTED_COMPONENTS), EXPECTED_EXEMPT)
    assert exempted == [], "istisno ISHLAMADI — predikat istisnoni umuman o'qimayapti"


# ---------------------------------------------------------------------------
# 5. `EXPECTED_COMPONENTS` jadvaldan HOSILA EMAS
# ---------------------------------------------------------------------------


def test_expected_components_is_not_derived_from_the_table() -> None:
    """Ro'yxat LITERAL kortej — `SELECT` dan yoki jadvaldan hosila EMAS.

    =========================================================================
    ⛔ BU FARQ BUTUN DARVOZANING MAZMUNI.

    Ro'yxat `system_heartbeats` dan o'qilsa «hech qachon yozilmagan
    komponent» tushunchasining O'ZI yo'qolardi: bo'sh jadval
    «kutilayotgan hech nima yo'q» degan ma'no berib, endpoint ⛔ `200 ok`
    qaytarardi — ya'ni worker UMUMAN ko'tarilmagan holat «hammasi joyida»
    bo'lib ko'rinardi.

    ⚠ AST BILAN, `grep` BILAN EMAS (03-07 / 07-13 ning o'lchangan darsi):
      grep izohni koddan ajratmaydi, ya'ni taqiqni TUSHUNTIRISH darvozani
      o'z-o'ziga qarshi qo'yardi.
    =========================================================================
    """
    tree = ast.parse(SELF_CHECK_PATH.read_text(encoding="utf-8"), filename=str(SELF_CHECK_PATH))
    values = dict(_module_level_assignments(tree))
    node = values.get("EXPECTED_COMPONENTS")
    assert node is not None, "`EXPECTED_COMPONENTS` modul darajasida topilmadi"

    assert isinstance(node, ast.Tuple), (
        f"`EXPECTED_COMPONENTS` endi literal kortej emas ({type(node).__name__}) — "
        "u jadvaldan yoki so'rovdan hosila bo'lib qolgan bo'lsa, bo'sh jadval "
        "`200 ok` berardi va worker o'lgani KO'RINMASDI"
    )
    non_literal = [
        ast.dump(element)
        for element in node.elts
        if not (isinstance(element, ast.Constant) and isinstance(element.value, str))
    ]
    assert non_literal == [], (
        f"`EXPECTED_COMPONENTS` da satr konstantasi bo'lmagan element bor: {non_literal}"
    )
    assert len(node.elts) == len(self_check.EXPECTED_COMPONENTS), (
        "manbadagi kortej uzunligi import qilingan qiymat bilan mos kelmadi — "
        "ro'yxat ish vaqtida o'zgartirilyapti"
    )
