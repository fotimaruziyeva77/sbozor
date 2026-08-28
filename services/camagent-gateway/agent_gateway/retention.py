"""Eski kadrlarni tozalash — disk to'lib qolmasin.

=============================================================================
NEGA KERAK (260828 da o'lchandi).

sbozor'ning o'z tozalagichi (`RETENTION_FULL_DAYS=90`) `camagent/`
prefiksiga ATAYIN tegmaydi — u faqat `{uuid}/{sana}/` yo'llarini
supuradi (`docs/integration.md` 0-bo'limi). Ya'ni CamAgent kadrlarini
hech kim o'chirmasdi va ular abadiy to'planardi.

O'lchangan hajm: haqiqiy kamera bitta kadrda ~400 KB beradi (spec'dagi
40 KB taxmini NVR sub-stream uchun edi). Bitta bozor:

    15 kamera x 8 slot x 400 KB  ~=  48 MB/kun  ~=  17 GB/yil
    12 bozor                                    ~= 210 GB/yil

387 GB disk bir yildan sal ko'proq yetardi, keyin server SEKIN emas,
TO'LIQ to'xtardi: yangi kadr ham yozilmaydi, baza ham yozolmaydi.

=============================================================================
⛔⛔ TARTIB O'ZGARMAYDI: AVVAL RASM, KEYIN METADATA.

Teskari tartibda metadata yo'qoladi va rasm obyekt xotirada QOLADI —
uni endi hech kim topa olmaydi, chunki havola faqat o'sha qatorda edi.
Bunday «yetim» rasm hech qachon o'chirilmaydi va tozalagich uni har
kuni qayta hisoblamaydi ham: u ko'rinmas chiqindi bo'lib qoladi.

⚠ RASM O'CHIRILMASA QATOR HAM QOLADI. Keyingi yugurish o'sha kadrni
  qayta uradi. Bu ATAYIN: obyekt xotira vaqtincha javob bermayotgan
  bo'lishi mumkin va metadata'ni yo'qotish qaytarib bo'lmaydigan ish.

⚠ DALIL MUDDATI — SOZLAMA, KOD EMAS. `CAMAGENT_GW_RETENTION_DAYS`
  standarti sbozor bilan bir xil: 90 kun. Nizo odatda bir necha kun
  ichida chiqadi; 90 kun buni ortig'i bilan qoplaydi.
=============================================================================
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass

from .db import GatewayDB
from .storage import SnapshotStorage

log = logging.getLogger("agent_gateway.retention")

DEFAULT_RETENTION_DAYS = 90
"""sbozor'ning `RETENTION_FULL_DAYS` bilan bir xil — ikki tizim bir xil
muddat saqlasin, aks holda «qaysi biri hali bor?» degan savol tug'ilardi."""

DEFAULT_BATCH = 500
"""Bir yugurishda nechta kadr. Chegara kerak: bir yillik to'planma o'n
minglab qator bo'ladi va ularni bitta o'tishda o'chirish SQLite'ni
bloklab, o'sha paytda kelgan kadrni RAD ETTIRARDI."""


@dataclass
class RetentionResult:
    """Bir yugurishning o'lchanadigan natijasi.

    ⛔ NOL — NATIJA, uning yo'qligi emas: hamma maydon HAR DOIM
       qaytariladi va chaqiruvchi «nega hech narsa o'chmadi?» savoliga
       javobni yonida topadi.
    """

    deleted: int = 0
    freed_bytes: int = 0
    failed: int = 0
    """Rasm o'chirilmadi — metadata ATAYIN qoldirildi, keyingi safar
    qayta uriniladi."""
    disabled: bool = False
    """Muddat 0 yoki manfiy — tozalash o'chirilgan."""


def retention_days() -> int:
    """Saqlash muddati (kun). 0 yoki manfiy — tozalash o'chiq."""
    raw = os.getenv("CAMAGENT_GW_RETENTION_DAYS", "").strip()
    if not raw:
        return DEFAULT_RETENTION_DAYS
    try:
        return int(raw)
    except ValueError:
        log.warning("CAMAGENT_GW_RETENTION_DAYS noto'g'ri: %r — %d kun ishlatiladi",
                    raw, DEFAULT_RETENTION_DAYS)
        return DEFAULT_RETENTION_DAYS


def sweep(
    db: GatewayDB,
    storage: SnapshotStorage,
    *,
    days: int | None = None,
    batch: int = DEFAULT_BATCH,
    now: float | None = None,
) -> RetentionResult:
    """Muddati o'tgan kadrlarni o'chiradi.

    Args:
        days: saqlash muddati. `None` bo'lsa muhitdan olinadi.
        batch: bir yugurishda nechta kadr.
        now: joriy vaqt (epoch). ARGUMENT — test uni qat'iy beradi va
            «kecha» degan tushuncha bitta qiymatga aylanadi.

    Returns:
        `RetentionResult`.
    """
    kun = retention_days() if days is None else days
    if kun <= 0:
        log.info("tozalash o'chirilgan (retention_days=%d)", kun)
        return RetentionResult(disabled=True)

    hozir = time.time() if now is None else now
    cutoff = hozir - kun * 86400.0
    natija = RetentionResult()

    for row in db.snapshots_older_than(cutoff, batch):
        ref = str(row["storage_ref"])
        try:
            ochirildi = storage.delete_snapshot(ref)
        except Exception:                             # noqa: BLE001
            # ⛔ TOZALASH HECH QACHON GATEWAY'NI YIQITMAYDI: bu fon ishi,
            #   kadr qabul qilish esa asosiy vazifa.
            log.exception("rasm o'chirishda xato: %s", ref)
            ochirildi = False

        if not ochirildi:
            natija.failed += 1
            continue

        db.delete_snapshot_row(str(row["idem_key"]))
        natija.deleted += 1
        natija.freed_bytes += int(row["size_bytes"] or 0)

    if natija.deleted or natija.failed:
        log.info("tozalash: %d o'chirildi (%.1f MB), %d urinish muvaffaqiyatsiz",
                 natija.deleted, natija.freed_bytes / 1048576, natija.failed)
    return natija
