"""Aniqlagich yadrosi — XOM TENZORDAN VERDIKTGACHA (AI-02, 05-07).

=============================================================================
CHOK (SEAM) `sv.Detections` DA — VA U BU PAKETNING MARKAZIY QARORI (D-02).

    postprocess.raw_to_detections()   xom tenzor  ->  sv.Detections
    ------------------------------------------------------------------ CHOK
    zones.zone_verdict()              sv.Detections -> verdikt

Chokdan YUQORISI («model to'g'ri javob berdimi?») real Karmana kadrini
talab qiladi va u bugun YO'Q — bu savol 05-VALIDATION ning «isbotlanmaydi»
ro'yxatida ochiq turadi.

Chokdan PASTGA tushadigan hamma narsa — arifmetika va geometriya —
sintetik `sv.Detections` bilan TO'LIQ isbotlanadi.

⚠⚠ IKKINCHISINING YASHILLIGI BILAN BIRINCHISINING YO'QLIGINI YOPISH
   TAQIQLANADI. Bu paketning testlari to'liq yashil bo'lganda ham model
   aniqligi haqida HECH NIMA o'lchanmagan bo'ladi. Loyiha bu shaklni ikki
   marta rad etgan (2-fazaning o'zini o'zi tasdiqlovchi shabloni,
   3-fazaning «simulyatordan kadr olib tekshiramiz» taklifi).

=============================================================================
NEGA `rfdetr` NING O'Z POST-PROCESSING KODI ISHLATILMAYDI.

`torch` — `rfdetr` ning MAJBURIY bog'liqligi, ekstrasi emas (D-04). Uni
o'rnatish ishlab chiqarish image'iga ~800 MB qo'shardi va u
`tests/unit/test_license_fence.py` ning uchala qatlamida ham TAQIQLANGAN.
Ya'ni bu paket eksport qilingan grafning xom chiqishini O'ZI hisoblaydi;
hisob-kitobning har bir bosqichi shu sababdan alohida darvoza ostida.
=============================================================================
"""

from __future__ import annotations
