"""`nvr-sim` — simulyatsiya qilingan Hikvision NVR (CAM-09).

⚠ BU PAKET **TEST USKUNASI**, ISHLAB CHIQARISH KODI EMAS.

U compose'da `profiles: ["sim"]` ortida yashaydi va profilsiz
`docker compose up` uni umuman ishga tushirmaydi — ya'ni prodga sizib
ketish **strukturaviy jihatdan** imkonsiz, intizom bilan emas (T-03-07).

Nega u umuman bor: tayyor Hikvision NVR emulyatori **mavjud emas** (ikki
mustaqil qidiruv bilan tasdiqlangan, `03-RESEARCH.md` B.6). Mockning butun
qiymati aynan **xato yo'llarini** ishonchli qayta tug'dirishida — noto'g'ri
parol, soat farqi, qulflangan hisob, `digest`-only firmware, offline kanal,
sessiya limiti — va bu tayyor emulyatorda baribir bo'lmasdi.

Nega `respx` yetarli emas: u `httpx` transportini almashtiradi, ya'ni
**Digest handshake umuman bajarilmaydi**, holbuki aynan handshake bizning
eng nozik joyimiz (A.3). `respx` "kod XML'ni parse qiladi" ni isbotlaydi,
"kod NVR bilan gaplasha oladi" ni **emas**.

BOG'LIQLIK BYUDJETI: bu paket **yangi paket qo'shmaydi**. U faqat FastAPI
(allaqachon `core-api` da) va stdlib (`hashlib`, `secrets`, `email.utils`,
`xml.etree`) ishlatadi va `services/core-api/Dockerfile` ning `dev`
target'ida ishlaydi — ya'ni CI'da qo'shimcha build vaqti ~0 (T-03-SC).
"""

from __future__ import annotations
