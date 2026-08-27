"""Snapshot obyektining S3 kaliti — deterministik fabrika (CAM-07, §D.9).

Sof funksiyalar moduli (`rtsp.py` bilan bir xil shakl): tarmoqqa
chiqmaydi, bazaga tegmaydi, holat saqlamaydi.

=============================================================================
UCH FAKT — UCHALASI HAM QAYTA MUHOKAMA QILINMAYDI.

1. TARTIB MUZOKARA QILINMAYDI: `market / sana / kamera / slot`.

   Eng katta ommaviy amal — RETENTION. U kunlik ishlaydi va bitta bozorning
   BARCHA kameralari ustidan yuradi. Bu tartibda u BITTA prefiks skani
   (`{market}/{sana}/`); `market/kamera/sana` tartibida esa N ta skan —
   har kamera uchun bittadan. 25 kamerali bozorda bu 25 barobar qimmat va
   xarajat bozorlar soni bilan ko'payadi.

   «Kameraning butun tarixi» so'rovi bu tartibda ham arzon: u
   `snapshots` jadvalining INDEKSIDAN keladi, S3 dan emas (2-band).

2. S3 HECH QACHON SO'ROV MEXANIZMI EMAS.

   `sbozor_core/security.py:6-11` uslubidagi «bu yo'l ATAYIN yo'q» izohi:
   `ListObjectsV2` FAQAT retention va yetim obyekt supurgisi uchun. Har
   qanday foydalanuvchi so'rovi BAZADAN javob oladi.

   Sabab arxitekturaviy: ombor almashishi (SeaweedFS -> AWS S3 ->
   O'zbekiston buluti) sozlama o'zgarishi bo'lib qolishi kerak. S3 listing
   so'rov semantikasiga aylansa, ombor almashishi SO'ROVLARNI ham
   o'zgartirardi va migratsiya arzon bo'lmasdi.

3. ⛔ KALIT FOYDALANUVCHI KIRITMASIDAN QURILMAYDI (T-04-27, ASVS V12.3).

   Segmentlar FAQAT `UUID`, ISO sana va `HHMM` formatidan hosil bo'ladi.
   Kamera nomi, bozor nomi yoki fayl nomi — hech qanday erkin matn kalitga
   KIRMAYDI, ya'ni `../` yozib bo'ladigan joy STRUKTURAVIY ravishda YO'Q.

   Bu «tozalash» (sanitizatsiya) EMAS va farq muhim: tozalash chetlab
   o'tilishi mumkin (kodlash, unicode, ikki marta dekodlash), struktura esa
   yo'q. Erkin matn qo'shish uchun avval IMZONI o'zgartirish kerak va bu
   diffda ko'rinadi — `rtsp.py` ning «parol parametri UMUMAN yo'q»
   qarori bilan aynan bir xil mexanizm.
=============================================================================

⚠ KALIT DETERMINISTIK — tasodifiy komponent YO'Q (§B.4). Siqilgan versiya
  AYNAN o'sha kalitni USTIGA yozadi: 6-fazadagi dalil havolalari hech
  qachon buzilmasligi kerak, ya'ni siqish kalitni o'zgartirmaydi. Tier
  `snapshots.storage_tier` da yashaydi, kalitda emas.

⚠ SLOT DAQIQA ANIQLIGIDA (`HHMM`), sekundsiz. Sekund kiritilsa retry
  ikkinchi obyekt yaratardi va `(market_id, camera_id, slot,
  business_date)` idempotentlik kaliti ombor darajasida buzilardi.
"""

from __future__ import annotations

from datetime import date, time
from uuid import UUID

__all__ = ["KEY_PREFIX_FOR_DAY", "OBJECT_SUFFIX", "object_key"]

OBJECT_SUFFIX = ".jpg"
"""Kadr HAR DOIM JPEG — siqilgandan keyin ham (retention faqat `quality=` ni tushiradi)."""

_SLOT_FORMAT = "%H%M"
"""`0630` — to'rt raqam, NOL BILAN TO'LDIRILGAN.

To'ldirilmagan shakl (`630`) leksikografik tartibni buzardi: `1800` <
`630` bo'lib chiqardi va retention'ning prefiks skani kunni noto'g'ri
tartibda o'qirdi.
"""


def object_key(
    *,
    market_id: UUID,
    business_date: date,
    camera_id: UUID,
    slot_time: time,
) -> str:
    """Bitta slot kadrining to'liq S3 kaliti.

    ⚠ ARGUMENTLAR FAQAT NOMLI (`*`). `market_id` va `camera_id` bir xil
      tipda, ya'ni pozitsion chaqiruvda ularni almashtirib yuborish TIP
      XATOSI BERMASDI — kalit «to'g'ri ko'rinishda» qurilardi va kadrlar
      boshqa bozorning prefiksiga tushardi. Nomli argument bu sinfni
      butunlay yopadi.

    Args:
        market_id: `markets.id` — kalitning BIRINCHI segmenti (bitta
            bucket, bozor boshiga prefiks; §D.9).
        business_date: Asia/Tashkent bo'yicha biznes-kun (1-fazada
            o'rnatilgan), UTC sanasi EMAS.
        camera_id: `cameras.id`.
        slot_time: jadvaldagi slot vaqti; sekundlar E'TIBORSIZ qoldiriladi.

    Returns:
        `{market_id}/{YYYY-MM-DD}/{camera_id}/{HHMM}.jpg`
    """
    return (
        f"{KEY_PREFIX_FOR_DAY(market_id=market_id, business_date=business_date)}"
        f"{camera_id}/{slot_time.strftime(_SLOT_FORMAT)}{OBJECT_SUFFIX}"
    )


def KEY_PREFIX_FOR_DAY(*, market_id: UUID, business_date: date) -> str:  # noqa: N802
    """Bir kunning BARCHA kadrlari uchun `ListObjectsV2` prefiksi.

    Retention va yetim obyekt supurgisi FAQAT shu funksiyadan foydalanadi.

    ⚠ `object_key` SHU FUNKSIYADAN QURILADI, aksincha emas. Ikkalasi
      mustaqil yozilsa prefiks bir kun kalitdan ajralib ketardi va
      retention JIMGINA hech nima topmasdi: xato yo'q, jurnal yozuvi yo'q,
      eski kadrlar esa muddatsiz saqlanib qolardi. Nosozlik faqat disk
      to'lganda ko'rinardi.

    ⚠ AJRATUVCHI BILAN TUGAYDI. Usiz `.../2026-09-1` prefiksi
      `.../2026-09-10` kunini ham ushlab olardi va retention noto'g'ri
      kunni o'chirardi.

    ⚠ NOM YUQORI REGISTRDA (`ruff` N802 shu yerda ATAYIN o'chirilgan): u
      chaqiruv joyida KONSTANTA kabi o'qiladi va «bu — kalit fabrikasining
      qismi, mustaqil so'rov emas» degan 2-faktni ko'rsatib turadi. Shakl
      reja kontraktida (`04-04-PLAN.md`) aynan shunday belgilangan.
    """
    return f"{market_id}/{business_date.isoformat()}/"
