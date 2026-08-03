"""Fon vazifalari — SOF `async def` funksiyalar, navbat kutubxonasidan MUSTAQIL.

=============================================================================
BU PAKETDA NAVBAT KUTUBXONASI IMPORT QILINMAYDI (D-06).

Har bir modul oddiy `async def` funksiya beradi; uni navbatga bog'laydigan
yupqa qobiq `app/worker.py` da yashaydi va kutubxona nomi FAQAT o'sha
faylda uchraydi.

Sabab 4-fazaga tegishli: ROADMAP orkestratsiya mexanizmini (`taskiq` vs
Postgres `SKIP LOCKED`) ochiq savol deb belgilagan. Mexanizm o'zgarsa
ko'chirish narxi ~10 QATOR bo'lishi kerak — butun kashfiyot mantig'ini
qayta yozish emas. Va **ikki mexanizm bir vaqtda saqlanmaydi**.

Ikkinchi, kundalik foyda: sof funksiyani test TO'G'RIDAN-TO'G'RI chaqiradi.
`tests/integration/test_nvr_discovery_job.py` worker konteynerini ham,
brokerni ham kutmaydi — u jobni funksiya sifatida ishga tushiradi va
natijani bazadan o'qiydi.
=============================================================================
"""

from __future__ import annotations
