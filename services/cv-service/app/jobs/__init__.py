"""`cv-service` ning fon-vazifalari.

⚠ BU DARAXTDA NAVBAT KUTUBXONASI IMPORT QILINMAYDI (D-06,
  `core-api/app/jobs/discovery.py:4-12` ning aynan o'sha qoidasi).
  `detect` — SOF `async def` funksiya; uni navbatga bog'laydigan yupqa
  qobiq `app/worker.py` da va `taskiq` nomi FAQAT o'sha faylda uchraydi.

  Buni `grep -cE "^\\s*(import|from)\\s+taskiq" app/jobs/` mexanik
  tekshiradi.
"""
