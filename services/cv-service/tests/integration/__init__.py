"""`cv-service` ning integratsiya testlari — HAQIQIY resurs talab qiladiganlar.

⚠ `tests/unit/` bilan farqi ATAYIN: bu yerdagi testlar jarayondan
tashqaridagi narsaga (bugun — ONNX artefakti, 05-08 dan boshlab —
Postgres va S3) tayanadi va shu sababdan ular MARKER bilan ajratiladi.

⚠ `tests/` ning O'ZI paket EMAS (`__init__.py` yo'q) — repo ildizidagi
  `tests/` bilan aynan bir xil shakl. Paket qilinsa `fixtures.detections`
  va `tests.fixtures.detections` bitta faylning ikki nomi bo'lib qolardi
  va `mypy` uni rad etardi (05-02 da o'lchangan).
"""

from __future__ import annotations
