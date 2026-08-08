#!/usr/bin/env python3
"""Oltin to'plam harness'i — UXLAB YOTGAN aniqlik darvozasi (W0-9, D-01/D-02).

=============================================================================
BU SKRIPT BUGUN BIRORTA ANIQLIK RAQAMINI CHIQARMAYDI — VA BU UNING BUTUN
MA'NOSI.

D-01: bu fazaning yetkazib berish mahsuloti aniqlik RAQAMI emas, uni
o'lchaydigan MASHINA. Haqiqat (real Karmana kadrlari) hali yo'q, ya'ni
o'lchash uchun narsa yo'q. Shuning uchun darvoza BUGUN quriladi va
UXLAB yotadi:

    karmana = [row for row in rows if row.source == "karmana"]
    if len(karmana) >= MIN_N:   -> darvoza QUROLLANADI
    aks holda                   -> hisobot chiqadi, darvoza qo'yilmaydi

⚠ UYG'ONISH UCHUN KOD O'ZGARTIRILMAYDI. Real kadrlar manifestga
  `source="karmana"` bilan qo'shilgan kuni shart o'z-o'zidan bajariladi.
  Keyin tahrirlanishi kerak bo'lgan harness — harness emas, u hujjatdagi
  niyat bo'lib qolardi.

  Mexanizm yangi emas: `sbozor_core.schema_contract.FINANCIAL_TABLES`
  aynan shu shaklda ishlaydi («jadval mavjud bo'lsa — konstrayt ham
  shart»; reyestr bugun bo'sh, darvoza kelajakda avtomatik yopiladi).

⛔ MATEMATIKA BU YERDA TAKRORLANMAYDI. Chalkashlik matritsasi va Wilson
  oralig'i `app/services/accuracy_report.py` da yashaydi (05-12) va bu
  skript uni IMPORT QILADI. Ikki nusxa matematika ikki xil raqam berardi
  va qaysi biri hisobotga tushgani aniqlanmasdi. Shuning uchun bu faylda
  na Wilson formulasi, na matritsa hisobi bor — faqat IMPORT NUQTASI
  (`ACCURACY_MODULE` / `LOWER_BOUND_ATTR`).

⛔ O'LCHANMAGAN FOIZ CHOP ETILMAYDI (T-05-04). Darvoza uxlagan holatda
  skript aniqlik foizini UMUMAN ko'rsatmaydi: raqamni ko'rsatish uni
  o'lchangan qilib ko'rsatardi, va o'sha raqam keyin taqdimotga,
  hisobotga, shartnomaga ko'chib ketardi.
=============================================================================

Ishga tushirish:

    python scripts/eval-golden-set.py --manifest tests/fixtures/golden_set/manifest.jsonl

Sxema va operatsion tartib: `tests/fixtures/golden_set/README.md`.
"""

from __future__ import annotations

import argparse
import importlib
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Protocol, cast

REPO_ROOT: Final = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST: Final = REPO_ROOT / "tests" / "fixtures" / "golden_set" / "manifest.jsonl"

MIN_N: Final = 73
"""Darvoza QUROLLANADIGAN eng kichik `karmana` namunasi.

Raqam TANLANMAGAN, `05-RESEARCH.md` §C.8.4 ning jadvalidan OLINGAN: haqiqiy
aniqlik ~95% bo'lganda ±5 foiz punkt kenglikdagi 95% ishonch oralig'i uchun
taxminan 73 ta yozuv kerak. Undan kichik namunada chiqadigan har qanday
foiz shunchalik keng oraliqqa ega bo'lardiki, u «aniqlik» degan so'zga
loyiq bo'lmasdi.
"""

THRESHOLD: Final = 0.85
"""Aniqlikning Wilson QUYI CHEGARASI uchun minimal qiymat.

⚠ BU RAQAM HAM HISOBLANGAN, TANLANMAGAN — va hisob shu yerda turadi,
chunki usiz u «taxminan to'g'ri ko'rinadigan» son bo'lib qolardi:

    n = MIN_N = 73, p = 0.95, z = 1.96  ->  Wilson quyi chegarasi = 0.8738

Ya'ni HAQIQATAN 95% aniq model minimal namunada 0.874 ga chiqadi. Agar
chegara 0.90 qilinsa, o'sha model darvozadan O'TA OLMASDI va yagona
«tuzatish» yo'li chegarani keyinroq, bosim ostida TUSHIRISH bo'lardi —
bo'shatiladigan darvoza esa darvoza emas. 0.85 — 95% li modelni
o'tkazadigan, 80% li modelni esa ushlaydigan eng yuqori yumaloq qiymat.

⚠ BU STANDART QIYMAT, O'LCHANGAN DA'VO EMAS. Real ma'lumot kelganda u
biznes qarori sifatida ATAYIN tasdiqlanadi yoki o'zgartiriladi (D-01:
faza mashinani beradi, raqamni emas).
"""

ACCURACY_MODULE: Final = "app.services.accuracy_report"
"""Chalkashlik matritsasi + Wilson matematikasining YAGONA manbai (05-12).

Import ATAYIN kechiktirilgan (`importlib`): modul bu rejada hali mavjud
emas va darvoza uxlab yotganda u UMUMAN kerak emas. Modul nomi shu yerda
BIR MARTA yozilgan — `tests/unit/test_golden_harness.py` aynan shu import
nuqtasining mavjudligini o'lchaydi.
"""

LOWER_BOUND_ATTR: Final = "accuracy_lower_wilson_bound"
"""`ACCURACY_MODULE` dan kutiladigan chaqiriluvchi: `(to'g'ri, jami) -> float`."""

ALLOWED_KEYS: Final = frozenset(
    {"image_ref", "polygon", "true_verdict", "source", "labeled_by", "labeled_at"}
)
VERDICTS: Final = frozenset({"occupied", "empty"})
SOURCES: Final = frozenset({"synthetic", "karmana"})
MIN_POLYGON_POINTS: Final = 3


@dataclass(frozen=True)
class GoldenRow:
    """Manifestning bitta satri — TEKSHIRILGAN holatda.

    `polygon` 0..1 normallashgan koordinatalarda (D-05): poligon kadr
    o'lchamiga bog'lanmaydi, ya'ni oqim o'lchami o'zgarganda zona qayta
    chizilmaydi.
    """

    image_ref: str
    polygon: tuple[tuple[float, float], ...]
    true_verdict: str
    source: str
    labeled_by: str
    labeled_at: str


class VerdictProvider(Protocol):
    """Bandlik verdiktini beradigan chaqiriluvchi — D-02 NING CHOKI.

    ⚠ BU REJADA AMALGA OSHIRILISH YOZILMAYDI va bu ataylab. Haqiqiy
      provayder (ONNX sessiyasi + `supervision.PolygonZone`) 05-12 da
      ulanadi. Interfeys esa BUGUN turadi, chunki D-02 seam'ni aynan shu
      joyda belgilaydi: modeldan keyingi hamma narsa to'liq testlanadi,
      modelning O'ZI esa oltin to'plam bilan o'lchanadi.

      Interfeysni keyinga qoldirish chokni ham keyinga qoldirardi va
      o'shanda «modelni almashtirsak nima o'zgaradi?» degan savolga
      javob beradigan yagona joy qolmasdi.
    """

    def __call__(self, image_ref: str, polygon: tuple[tuple[float, float], ...]) -> str: ...


def _fail(message: str) -> None:
    """Baland ovozda yiqiladi — JIMGINA O'TKAZIB YUBORISH YO'LI YO'Q.

    `assert` ATAYIN ishlatilmaydi: `python -O` ostida u BUTUNLAY
    o'chiriladi, ya'ni darvoza bir bayroq bilan jimgina yo'qolardi.
    """
    raise SystemExit(f"eval-golden-set: {message}")


def _parse_polygon(raw: Any, line_no: int) -> tuple[tuple[float, float], ...]:
    """Poligonni tekshiradi: kamida 3 nuqta, har biri 0..1 oralig'ida."""
    if not isinstance(raw, list) or len(raw) < MIN_POLYGON_POINTS:
        _fail(
            f"{line_no}-satr: `polygon` kamida {MIN_POLYGON_POINTS} nuqtali ro'yxat bo'lishi shart"
        )

    points: list[tuple[float, float]] = []
    for point in cast("list[Any]", raw):
        if not isinstance(point, list) or len(point) != 2:
            _fail(f"{line_no}-satr: `polygon` nuqtasi `[x, y]` shaklida bo'lishi shart")
        pair = cast("list[Any]", point)
        if not all(isinstance(value, int | float) for value in pair):
            _fail(f"{line_no}-satr: `polygon` koordinatalari son bo'lishi shart")
        x, y = float(pair[0]), float(pair[1])
        if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
            _fail(
                f"{line_no}-satr: `polygon` koordinatasi 0..1 dan tashqarida: ({x}, {y}). "
                "Zona koordinatalari NORMALLASHGAN bo'lishi shart (D-05)."
            )
        points.append((x, y))
    return tuple(points)


def load_manifest(path: Path) -> list[GoldenRow]:
    """Manifestni o'qiydi va HAR SATRNI tekshiradi.

    ⚠ NOMA'LUM KALIT HAM, YETISHMAGAN MAYDON HAM `SystemExit(1)` BERADI.
      «Tushunmagan satrni o'tkazib yuborish» yo'li ATAYIN yo'q: o'sha yo'l
      bilan xato yozilgan `source="karmana "` (ortiqcha probel) satrlari
      jimgina tashlab yuborilardi va darvoza HECH QACHON uyg'onmasdi —
      hech kim sababini bilmasdi.
    """
    if not path.is_file():
        _fail(f"manifest topilmadi: {path}")

    rows: list[GoldenRow] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload: Any = json.loads(line)
        except json.JSONDecodeError as error:
            _fail(f"{line_no}-satr yaroqli JSON emas: {error}")
        if not isinstance(payload, dict):
            _fail(f"{line_no}-satr JSON obyekti emas")

        record = cast("dict[str, Any]", payload)
        keys = set(record)
        unknown = keys - ALLOWED_KEYS
        if unknown:
            _fail(f"{line_no}-satrda noma'lum kalit(lar): {sorted(unknown)}")
        missing = ALLOWED_KEYS - keys
        if missing:
            _fail(f"{line_no}-satrda maydon yetishmayapti: {sorted(missing)}")

        if record["true_verdict"] not in VERDICTS:
            _fail(f"{line_no}-satr: `true_verdict` {sorted(VERDICTS)} dan biri bo'lishi shart")
        if record["source"] not in SOURCES:
            _fail(f"{line_no}-satr: `source` {sorted(SOURCES)} dan biri bo'lishi shart")
        for field in ("image_ref", "labeled_by", "labeled_at"):
            if not isinstance(record[field], str) or not record[field].strip():
                _fail(f"{line_no}-satr: `{field}` bo'sh bo'lmagan satr bo'lishi shart")

        rows.append(
            GoldenRow(
                image_ref=str(record["image_ref"]),
                polygon=_parse_polygon(record["polygon"], line_no),
                true_verdict=str(record["true_verdict"]),
                source=str(record["source"]),
                labeled_by=str(record["labeled_by"]),
                labeled_at=str(record["labeled_at"]),
            )
        )

    if not rows:
        _fail(f"manifest BO'SH: {path} — bo'sh to'plamda har qanday darvoza jimgina o'tardi")
    return rows


def run_gate(
    rows: Sequence[GoldenRow],
    *,
    min_n: int,
    threshold: float,
    provider: VerdictProvider | None = None,
) -> int:
    """Aniqlik darvozasi — UXLAB YOTGAN yoki QUROLLANGAN.

    Qaytaradi: jarayon chiqish kodi (0 — o'tdi, 1 — darvoza yiqildi).
    """
    karmana = [row for row in rows if row.source == "karmana"]
    synthetic = [row for row in rows if row.source == "synthetic"]

    print(f"manifest:  {len(rows)} yozuv ({len(synthetic)} synthetic, {len(karmana)} karmana)")

    if len(karmana) < min_n:
        # ⛔ BU YERDA FOIZ CHOP ETILMAYDI. Sintetik yozuvlar MEXANIKANI
        #    o'lchaydi, modelni EMAS — ular ustidan hisoblangan «aniqlik»
        #    ma'nosiz, lekin ko'rilgan zahoti ma'noli deb o'qilardi.
        print(
            f"darvoza:   UXLAYAPTI — {len(karmana)}/{min_n} karmana yozuvi.\n"
            "           Aniqlik O'LCHANMAGAN va shuning uchun CHOP ETILMAYDI (D-01).\n"
            '           Real kadrlar `source="karmana"` bilan qo\'shilganda bu\n'
            "           darvoza KOD O'ZGARMASDAN qurollanadi."
        )
        return 0

    if provider is None:
        # Darvoza UYG'ONDI, lekin o'lchaydigan narsa yo'q. Bu HOLAT
        # `return 0` bilan yopilmaydi: aynan o'sha yo'l «real ma'lumot
        # keldi, lekin hech nima o'lchanmadi» degan jimgina nosozlikni
        # yashirardi.
        _fail(
            f"{len(karmana)} ta karmana yozuvi bor (>= {min_n}), ya'ni darvoza UYG'ONDI, "
            "lekin verdikt provayderi ulanmagan. 05-12 `VerdictProvider` ni "
            f"`{ACCURACY_MODULE}` bilan birga ulaydi."
        )

    accuracy_module = importlib.import_module(ACCURACY_MODULE)
    lower_bound = cast("Callable[[int, int], float]", getattr(accuracy_module, LOWER_BOUND_ATTR))

    correct = sum(
        1
        for row in karmana
        if cast("VerdictProvider", provider)(row.image_ref, row.polygon) == row.true_verdict
    )
    bound = lower_bound(correct, len(karmana))
    print(f"darvoza:   QUROLLANGAN — aniqlikning Wilson quyi chegarasi = {bound:.4f}")

    if bound < threshold:
        print(f"NATIJA:    YIQILDI — {bound:.4f} < {threshold}")
        return 1
    print(f"NATIJA:    O'TDI — {bound:.4f} >= {threshold}")
    return 0


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="eval-golden-set",
        description="Oltin to'plam ustidan aniqlik darvozasi (uxlab yotadi — W0-9).",
    )
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--min-n", type=int, default=MIN_N)
    parser.add_argument("--threshold", type=float, default=THRESHOLD)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    rows = load_manifest(Path(args.manifest))
    return run_gate(rows, min_n=int(args.min_n), threshold=float(args.threshold))


if __name__ == "__main__":
    raise SystemExit(main())
