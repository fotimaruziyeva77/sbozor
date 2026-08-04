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

=============================================================================
OCHIQ SAVOL YOPILDI (D-02): IKKALASI HAM, LEKIN HAR BIRI O'Z ISHIDA.

Savolning shakli noto'g'ri edi — «`taskiq` YOKI `SKIP LOCKED`» tanlovi
emas, MEHNAT TAQSIMOTI:

    `taskiq scheduler`  ->  FAQAT holatsiz 1-daqiqalik tik ("* * * * *")
    Postgres            ->  REJA, ijara, idempotentlik va yo'qlik yozuvi

Mexanizm: `capture_repo.claim_due()` — `SELECT ... FOR UPDATE SKIP LOCKED`
+ `locked_until` ijarasi (`app/jobs/capture.py` uni tikning 4-qadamida
chaqiradi).

⚠ SABAB O'LCHANGAN, TANLANMAGAN: `taskiq` ning cron holati
(`SchedulerLoop.cron_tasks_last_run`) — jarayon XOTIRASIDAGI `dict` va
taqsimlangan qulf YO'Q. Ya'ni slot-boshiga cron planer 40 soniyaga o'lgan
paytda 06:00 slotini **izsiz** yo'qotardi: navbatda vazifa yo'q, jurnalda
qator yo'q, alert yo'q — CAM-05 ning o'z talabiga ZID. Reja Postgres'da
bo'lganda esa o'sha slot `pending` qator bo'lib turadi va keyingi tik
(<=60 s) uni oladi; grace oynasidan chiqsa `missed` YOZUVI qoladi.

Narxi bitta va u shu paketning eng jim xato sinfi: tik HAMMA bozorlar
ustida yurishi kerak, `sbozor_app` esa tenant kontekstisiz BIRORTA
bozorni ko'rmaydi (`capture.py` ning Pitfall 9 bo'limi).
=============================================================================

Ikkinchi, kundalik foyda: sof funksiyani test TO'G'RIDAN-TO'G'RI chaqiradi.
`tests/integration/test_nvr_discovery_job.py` worker konteynerini ham,
brokerni ham kutmaydi — u jobni funksiya sifatida ishga tushiradi va
natijani bazadan o'qiydi.
=============================================================================
"""

from __future__ import annotations
