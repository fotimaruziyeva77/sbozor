"""`cv-service` test to'plamining umumiy sozlamasi.

=============================================================================
⚠ BU TO'PLAM SOF — BAZA FIXTURE'I YO'Q VA U ATAYIN QO'SHILMAGAN.

Repo ildizidagi `tests/conftest.py` `testcontainers` bilan HAQIQIY
Postgres ko'taradi (tenant izolyatsiyasi RLS'siz sinalmaydi). Bu yerda esa
sinaladigan narsa boshqa: zona geometriyasi, xom tenzor arifmetikasi va
sintetik `sv.Detections` — ularning hech biriga baza KERAK EMAS.

Baza kerak bo'ladigan integratsiya testlari 05-08 da tug'iladi va o'sha
reja fixture'ni O'ZI qo'shadi. Uni bugundan qo'yish `testcontainers` ni bu
image'ga olib kirardi — ya'ni ikkinchi bog'liqlik to'plamini kattalashtirib,
hech nimani isbotlamasdi.

=============================================================================
YO'LLAR `pyproject.toml` DA, BU YERDA EMAS.

`[tool.pytest.ini_options] pythonpath = [".", "tests"]` `app` va
`fixtures` paketlarini topadi; `sbozor_core` esa venv'ga editable
o'rnatilgan (`[tool.uv.sources]`). Ya'ni `sys.path` ni QO'LDA o'zgartirish
KERAK EMAS va u qilinmaydi: qo'lda qo'shilgan yo'l pytest ning o'z
mexanizmi bilan ajralib ketardi va `mypy` uni umuman ko'rmasdi.
=============================================================================
"""

from __future__ import annotations
