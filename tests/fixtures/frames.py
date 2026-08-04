"""Sintetik JPEG generatori — kadr FIZIK XUSUSIYATI bo'yicha yasaladi (W0-9).

=============================================================================
MAJBURIYAT 1 — NOMLASH QOIDASI: FIZIK XUSUSIYAT, DETEKTOR VERDIKTI EMAS.

Bu modulning funksiyalari, parametrlari va uni ishlatadigan testlarning
nomlari FAQAT o'lchanadigan fizik xususiyat bilan ataladi:

    frame_bytes(mean=8, stddev=2)        ✅
    test_mean_8_stddev_2_reads_back...   ✅

    frame_dark() / frame_blank()         ❌
    test_dark_frame_is_rejected()        ❌

⚠ SABABI TO'G'RIDAN-TO'G'RI: chegara bilan nomlangan fixture testni O'Z
  FARAZINING AKS-SADOSIGA aylantiradi. `frame_rejected_by_filter()` degan
  fixture "filtr rad etadigan kadr" ni yasash uchun filtrning CHEGARASINI
  bilishi kerak — ya'ni u chegarani chegaraning O'ZI bilan tekshiradi va
  chegara noto'g'ri qo'yilgan bo'lsa ham YASHIL qoladi. Sifat filtri
  shunda darvoza emas, konventsiya bo'lib qolardi.

  Chegaralar 04-CONTEXT D-15 bo'yicha ATAYIN sozlanadigan va hozircha LOW
  ishonchda (real Karmana kadri yo'q). Ya'ni ular O'ZGARADI. Fizik
  xususiyat esa o'zgarmaydi: `mean=8` kadr chegara qanday qo'yilishidan
  qat'i nazar `mean=8` bo'lib qoladi. Fixture aynan shu qatlamda turadi.

  Bu modul sifat filtrini UMUMAN import qilmaydi va uning chegaralarini
  BILMAYDI. Filtrning o'z testi `04-04` da yoziladi va u shu yerdagi
  generatorni ISTE'MOL qiladi — teskarisi hech qachon emas.

=============================================================================
MAJBURIYAT 2 — DETERMINIZM: BIR XIL ARGUMENT -> BIR XIL BAYTLAR.

Shovqin `random` GLOBAL modulidan OLINMAYDI. Qadalgan urug'li mustaqil
generator (`random.Random(_SEED)`) ishlatiladi va u har chaqiruvda YANGIDAN
quriladi — modul darajasida umumiy holat yo'q (`karmana_seed.py` bilan
AYNAN bir xil qaror va bir xil sabab).

⚠ Usiz keyingi rejalarning chegara testlari "gohida yiqiladigan" turdagi
  bo'lardi: kadr baytlari har chaqiruvda o'zgarib, o'lchangan `mean`/
  `stddev` chegaraning atrofida sakrab turardi va sabab test mantig'ida
  emas, generatorda bo'lardi. Determinizm shuning uchun ALOHIDA test bilan
  o'lchanadi (`test_frame_fixtures.py`) — u tolerans testlaridan mustaqil.

=============================================================================
QANDAY ISHLAYDI VA NEGA AYNAN SHUNDAY.

Kadr — 8 piksel kengligidagi VERTIKAL polosalar to'plami. Har polosa BIR XIL
rangda, polosalarning yarmi `mean - stddev`, yarmi `mean + stddev`.

  * Ikki darajali muvozanatli taqsimotning standart og'ishi AYNAN `stddev`,
    o'rtachasi AYNAN `mean` — ya'ni nishon TASODIFGA tayanmaydi, u
    arifmetik natija.
  * Polosa kengligi 8 va u JPEG ning 8x8 DCT to'riga TUSHADI: har DCT bloki
    bir xil rangli bo'lgani uchun faqat DC koeffitsiyenti qoladi va
    kvantlash amalda yo'qotish keltirmaydi.
  * Polosalar TARTIBI qadalgan urug' bilan aralashtiriladi. Muntazam
    almashinuv (past-yuqori-past-yuqori) sof davriy signal bo'lardi; real
    kadr davriy emas va davriylikka tasodifan bog'lanib qolgan keyingi
    bosqich (5-faza) buni sezmasdi. Aralashtirish statistikani
    O'ZGARTIRMAYDI (to'plam o'sha), faqat davriylikni yo'qotadi — shu
    sababdan u determinizm testining ham yagona nishoni.

TOLERANS (O'LCHANGAN, 2026-08-04, Pillow 12.x):

  | Nima            | Kuzatilgan eng yomon xato |
  |-----------------|---------------------------|
  | `mean`          | ±0,5  (quality 30…95)     |
  | `stddev`        | ±1,0  (quality 30…95)     |
  | HSV to'yinganlik| ±0,01                     |

  E'LON QILINGAN kontrakt kengroq: `mean ±2`, `stddev ±1,5`. Farq ataylab —
  Pillow enkoderining versiya siljishiga zaxira. Testlar E'LON QILINGAN
  kontraktni ishlatadi, kuzatilgan qiymatni EMAS: aks holda Pillow yangilanishi
  generator to'g'ri ishlayotgan holda ham CI'ni qizartirardi.

CLI (`karmana_seed.py` naqshi) — kadrni ko'z bilan ham ko'rish uchun:

    PYTHONPATH=tests python -m fixtures.frames --out-dir ops/data/frames/local
"""

from __future__ import annotations

import argparse
import io
import random
from pathlib import Path
from typing import Final

from PIL import Image

__all__ = [
    "HTML_ERROR_PAGE",
    "MAX_LEVEL",
    "MEAN_TOLERANCE",
    "SATURATION_TOLERANCE",
    "STDDEV_TOLERANCE",
    "frame_bytes",
    "truncate",
]

_SEED: Final = 20260804
"""Qadalgan urug'. Qiymatning O'ZI ahamiyatsiz — QADALGANLIGI ahamiyatli."""

_BAND_WIDTH: Final = 8
"""Polosa kengligi = JPEG DCT blokining kengligi.

Bu son ERKIN TANLANMAGAN: 8 dan boshqa qiymat (masalan 4) polosani DCT
blokining ICHIGA joylashtirardi va kvantlash chegara qiymatlarini yeb
qo'yardi. 16 ham ishlardi, lekin u 4:2:0 xrominant kamaytirishga zaxira
bo'lgan bo'lardi — bu yerda esa `subsampling=0` (4:4:4) ochiq berilgan.
"""

MAX_LEVEL: Final = 255

MEAN_TOLERANCE: Final = 2.0
STDDEV_TOLERANCE: Final = 1.5
SATURATION_TOLERANCE: Final = 0.05
"""E'LON QILINGAN kontrakt (modul docstringidagi jadvalga qarang).

Ular MODULDA yashaydi, testda emas: tolerans generatorning va'dasi, testning
qulayligi emas. Test uni FAQAT o'qiydi.
"""

# ITU-R 601-2 — `PIL.Image.convert("L")` aynan shu koeffitsiyentlarni
# ishlatadi. Ular shu yerda TAKRORLANADI, chunki to'yinganlik kiritilganda
# yorug'likni saqlab qolish uchun teskari hisob kerak (pastga qarang).
_LUMA_R: Final = 0.299
_LUMA_G: Final = 0.587
_LUMA_B: Final = 0.114

_HTML_ERROR_TEXT: Final = (
    "<html>\n"
    "<head><title>401 Unauthorized</title></head>\n"
    "<body>\n"
    "<h1>401 Unauthorized</h1>\n"
    "<p>The requested URL requires authorization.</p>\n"
    "</body>\n"
    "</html>\n"
)

HTML_ERROR_PAGE: Final[bytes] = _HTML_ERROR_TEXT.encode("utf-8")
"""NVR/go2rtc xato sahifasi — `image/jpeg` o'rniga KELADIGAN tana.

⚠ TUZOQ `Content-Type` da EMAS, BAYTLARDA. Real qurilma bu sahifani
  ko'pincha `200 OK` bilan beradi va sarlavhada baribir `text/html` yozadi —
  lekin ba'zi proxy va firmware sarlavhani `image/jpeg` qoldirib yuboradi.
  Ya'ni `Content-Type` ga ishonadigan kod HTML sahifani YAROQLI KADR deb
  qabul qilardi (T-04-10). Yagona ishonchli tekshiruv — magic baytlar.
"""


def _rgb_for(level: float, saturation: float) -> tuple[int, int, int]:
    """Berilgan YORUG'LIK va TO'YINGANLIK uchun RGB uchligi.

    `saturation == 0` -> uchala kanal TENG. Bu IR (tungi) kadrning fizik
    xususiyati: IR yorituvchi bitta to'lqin uzunligida ishlaydi va sensor
    monoxrom kadr beradi. `light_mode` ning `ir_night` shoxi aynan shunga
    tayanadi (D-12), shuning uchun u ALOHIDA boshqariladigan o'lcham.

    `saturation > 0` -> `R = M` (eng katta), `B = m = M(1-s)` (eng kichik),
    `G = (M+m)/2`. HSV ta'rifi bo'yicha to'yinganlik `(M-m)/M = s`.

    ⚠ YORUG'LIK SAQLANADI. Kanallarni shunchaki bir-biridan uzoqlashtirish
      o'rtacha yorug'likni ham siljitardi va `mean` nishoni to'yinganlik
      bilan birga suzib ketardi — ya'ni ikki fizik xususiyat bir-biriga
      bog'lanib qolardi. Shuning uchun `M` teskari hisoblanadi:
          L = 0.299M + 0.587(M+m)/2 + 0.114m,  m = M(1-s)
          =>  M = L / (0.299 + 0.587/2 + (0.587/2 + 0.114)(1-s))
    """
    if saturation <= 0.0:
        value = round(level)
        return (value, value, value)

    divisor = _LUMA_R + _LUMA_G / 2 + (_LUMA_G / 2 + _LUMA_B) * (1.0 - saturation)
    top = level / divisor
    bottom = top * (1.0 - saturation)
    return (round(top), round((top + bottom) / 2), round(bottom))


def _validate(
    *, mean: int, stddev: int, saturation: float, size: tuple[int, int], quality: int
) -> None:
    """Nishonga tushib bo'lmaydigan argumentni QISIB emas, RAD ETIB qaytaradi.

    ⚠ Jimgina qisish (`clamp`) bu yerda eng yomon yechim bo'lardi: chaqiruvchi
      `mean=8, stddev=20` so'rab, `mean≈10` bo'lgan kadr olardi va tolerans
      testi qizarganda sabab test mantig'ida izlanardi. Modul o'z
      kontraktini bajara olmasa buni AYTISHI kerak.
    """
    width, height = size
    if width % _BAND_WIDTH:
        raise ValueError(
            f"width={width} — {_BAND_WIDTH} ga karrali bo'lishi SHART. "
            "Polosa JPEG ning 8x8 DCT to'riga tushmasa e'lon qilingan tolerans "
            "buziladi (o'lchandi 2026-08-04: width=100, mean=140 so'ralgan -> 134,6 "
            f"o'qilgan, ya'ni {MEAN_TOLERANCE} chegarasidan tashqarida)."
        )
    if width <= 0 or height <= 0:
        raise ValueError(f"size={size} — ikkala o'lcham ham musbat bo'lishi SHART")
    if stddev < 0:
        raise ValueError(f"stddev={stddev} — manfiy bo'la olmaydi")
    if not 0.0 <= saturation <= 1.0:
        raise ValueError(f"saturation={saturation} — [0,0; 1,0] oralig'ida bo'lishi SHART")
    if not 1 <= quality <= 95:
        raise ValueError(
            f"quality={quality} — [1; 95] oralig'ida bo'lishi SHART (Pillow chegarasi)"
        )

    low = mean - stddev
    high = mean + stddev
    if low < 0 or high > MAX_LEVEL:
        raise ValueError(
            f"mean={mean}, stddev={stddev} -> [{low}; {high}] oralig'i "
            f"[0; {MAX_LEVEL}] dan chiqib ketdi"
        )

    if saturation > 0.0:
        brightest = _rgb_for(high, saturation)[0]
        if brightest > MAX_LEVEL:
            raise ValueError(
                f"mean={mean}, stddev={stddev}, saturation={saturation} -> eng yorug' "
                f"kanal {brightest} (> {MAX_LEVEL}). To'yinganlikni oshirish eng katta "
                "kanalni ko'taradi; yorug'likni pasaytiring yoki to'yinganlikni kamaytiring."
            )


def frame_bytes(
    *,
    mean: int,
    stddev: int,
    saturation: float = 0.0,
    size: tuple[int, int] = (320, 180),
    quality: int = 85,
) -> bytes:
    """Berilgan FIZIK XUSUSIYATGA ega yaroqli JPEG.

    Args:
        mean: kul rang kanalining nishon o'rtachasi (`ImageStat.mean[0]`).
        stddev: nishon standart og'ish (`ImageStat.stddev[0]`).
        saturation: HSV to'yinganligi `0.0` (monoxrom / IR) … `1.0`.
        size: `(kenglik, balandlik)`. Kenglik 8 ga karrali bo'lishi SHART.
        quality: JPEG sifati (Pillow shkalasi).

    Returns:
        To'liq JPEG bayt oqimi — `\\xff\\xd8\\xff` bilan boshlanadi,
        `\\xff\\xd9` (EOI) bilan tugaydi.

    Raises:
        ValueError: nishonga tushib bo'lmasa (`_validate` ga qarang).
    """
    _validate(mean=mean, stddev=stddev, saturation=saturation, size=size, quality=quality)

    width, height = size
    band_count = width // _BAND_WIDTH
    high_count = band_count // 2
    levels: list[int] = [mean + stddev] * high_count + [mean - stddev] * (band_count - high_count)

    # HAR CHAQIRUVDA YANGI generator: modul darajasidagi umumiy holat
    # ikkinchi chaqiruvni birinchisiga bog'lab qo'yardi.
    #
    # S311: bu KRIPTOGRAFIYA emas — bu TAKRORLANADIGAN test yuki
    # (`karmana_seed.py:481-484` bilan bir xil sabab). Kriptografik
    # generator bu yerda AYNAN NOTO'G'RI vosita bo'lardi: uni qadab
    # bo'lmaydi, ya'ni determinizm yo'qolardi.
    random.Random(_SEED).shuffle(levels)  # noqa: S311

    palette = [_rgb_for(float(level), saturation) for level in levels]
    row = [palette[column // _BAND_WIDTH] for column in range(width)]

    image = Image.new("RGB", size)
    image.putdata(row * height)

    buffer = io.BytesIO()
    # `subsampling=0` -> 4:4:4. Standart 4:2:0 xrominantni gorizontal ikki
    # barobar kamaytiradi va to'yinganlik nishonini polosa chegarasida
    # yuvardi. `optimize=False` -> Huffman jadvali qayta hisoblanmaydi,
    # ya'ni chiqish Pillow ning ichki holatiga bog'liq bo'lmaydi.
    image.save(buffer, "JPEG", quality=quality, subsampling=0, optimize=False)
    return buffer.getvalue()


def truncate(data: bytes, keep: float = 0.6) -> bytes:
    """Oqimning oxirini kesadi — EOI (`\\xff\\xd9`) YO'QOLADI.

    Bu «yarim yetkazilgan javob» ning aynan shakli: TCP uzilishi, NVR ning
    bufer to'lib ketishi yoki proxy timeout'i JPEG ni o'rtasida uzadi.
    Sarlavha va birinchi skanerlash qatorlari YAROQLI bo'lgani uchun
    `Image.open()` MUVAFFAQIYATLI bo'ladi va xato faqat `load()` da chiqadi
    (`OSError: image file is truncated`) — shuning uchun sifat filtri
    `open()` bilan cheklanib qolsa buzuq kadrni yaroqli deb qabul qilardi.

    ⚠ `keep` [0,0; 1,0) oralig'ida: `1.0` hech nima kesmagan bo'lardi va
      funksiya jimgina o'z ma'nosini yo'qotardi.
    """
    if not 0.0 <= keep < 1.0:
        raise ValueError(f"keep={keep} — [0,0; 1,0) oralig'ida bo'lishi SHART")
    if not data:
        raise ValueError("bo'sh oqimni kesib bo'lmaydi")
    return data[: max(1, int(len(data) * keep))]


# ---------------------------------------------------------------------------
# CLI — kadrni ko'z bilan ko'rish uchun (`karmana_seed.py` naqshi).
# ---------------------------------------------------------------------------

_SAMPLES: Final[tuple[tuple[str, dict[str, int | float]], ...]] = (
    # ⚠ NOMLAR FIZIK XUSUSIYAT BILAN. Bu ro'yxatda `dark`, `blank`,
    #   `low_light` degan nom YO'Q va bo'lmaydi — modul docstringiga qarang.
    ("frame_mean_8_stddev_2", {"mean": 8, "stddev": 2}),
    ("frame_mean_30_stddev_3", {"mean": 30, "stddev": 3}),
    ("frame_mean_60_stddev_0", {"mean": 60, "stddev": 0}),
    ("frame_mean_128_stddev_40", {"mean": 128, "stddev": 40}),
    ("frame_mean_140_stddev_45_saturation_050", {"mean": 140, "stddev": 45, "saturation": 0.5}),
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Sintetik kadrlarni faylga yozadi (ko'z bilan ko'rish uchun)."
    )
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args(argv)

    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    for name, kwargs in _SAMPLES:
        mean = int(kwargs["mean"])
        stddev = int(kwargs["stddev"])
        saturation = float(kwargs.get("saturation", 0.0))
        data = frame_bytes(mean=mean, stddev=stddev, saturation=saturation)
        (out_dir / f"{name}.jpg").write_bytes(data)
        print(f"{name}.jpg  {len(data)} bayt")

    truncated = truncate(frame_bytes(mean=128, stddev=40))
    (out_dir / "frame_mean_128_stddev_40_truncated.bin").write_bytes(truncated)
    print(f"frame_mean_128_stddev_40_truncated.bin  {len(truncated)} bayt (EOI yo'q)")

    (out_dir / "http_error_body.html").write_bytes(HTML_ERROR_PAGE)
    print(f"http_error_body.html  {len(HTML_ERROR_PAGE)} bayt (JPEG EMAS)")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
