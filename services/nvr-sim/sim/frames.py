"""Kadr BAYTLARI — `frame_mode` ning to'rt qiymati (W0-10).

=============================================================================
NEGA BU MODUL UMUMAN BOR: MediaMTX BUZUQ KADR BERA OLMAYDI.

`nvr-sim-rtsp` (MediaMTX + ffmpeg) YAROQLI oqim beradi — bu uning ishi va u
buni yaxshi bajaradi. Ya'ni undan «yarmida uzilgan JPEG», «JPEG o'rniga HTML
xato sahifasi» yoki «bo'sh tana» ni OLIB BO'LMAYDI: bunday javob protokol
darajasida yaroqsiz bo'lardi va server uni umuman yubormasdi.

Lekin real NVR aynan shularni beradi:
  * tarmoq uzilishi          -> yarim yetkazilgan JPEG,
  * sessiya muddati tugashi  -> `<html>401</html>` sahifasi `200` bilan,
  * kanal band bo'lishi      -> `Content-Length: 0`.

Sifat filtri (04-04) shu javoblarni RAD ETISHI kerak. Baytlar sim
BOSHQARUVIDA bo'lmasa, filtr hech qachon buzuq kadr KO'RMASDI va u
darvoza emas, KONVENTSIYA bo'lib qolardi — bu rejaning butun sababi.

=============================================================================
KONSTANTA QAYERDAN KELDI (va nega bu YAGONA ruxsat etilgan takrorlanish).

`_BASE_JPEG_B64` — `tests/fixtures/frames.py` ning chiqishi:

    PYTHONPATH=tests python -c "import base64,sys; sys.path.insert(0,'tests'); \\
      from fixtures.frames import frame_bytes; \\
      print(base64.b64encode(frame_bytes(mean=128, stddev=40)).decode())"

    -> mean≈128, stddev≈40, 320x180, quality=85, 2927 bayt

⚠ NEGA NUSXA, IMPORT EMAS: `nvr-sim` konteyneri `tests/` ni ko'radi
  (`.:/app` mount), lekin unga TAYANISHI mumkin emas — sim QURILMANI
  modellaydi va qurilma test kodini import qilmaydi. Muhimrog'i: bu modul
  `Pillow` ga bog'lanmasligi SHART. Sim `core-api` ning `dev` image'ida
  ishlaydi va unga bitta ham qo'shimcha paket kiritilmaydi (T-04-SC).

⚠ Konstanta YANGILANSA, uni yuqoridagi buyruq bilan QAYTA hosil qiling —
  qo'lda tahrirlangan base64 jimgina buzuq JPEG beradi va sabab
  `frame_mode="ok"` testining «bu yaroqli kadr emas» xatosida ko'rinardi.
"""

from __future__ import annotations

import base64
from typing import Final

FRAME_MODES: Final[frozenset[str]] = frozenset({"ok", "truncated", "html", "empty"})
"""`SimState.frame_mode` ning ruxsat etilgan qiymatlari.

⚠ Bu to'plam `SIM_MODES` dan ALOHIDA va ular BIRLASHTIRILMAYDI. `mode` —
  ULANISH/AUTENTIFIKATSIYA o'lchami (`bad_password`, `clock_drift`, …),
  `frame_mode` esa JAVOB BAYTLARI o'lchami. Bittaga yig'ilganda «noto'g'ri
  parol VA buzuq kadr» kombinatsiyasini ifodalab bo'lmasdi — holbuki 04-04
  ning retry siyosati aynan shu ikkisini AJRATISHI kerak (birinchisida
  qayta urinish ZARARLI, ikkinchisida FOYDALI).
"""

_TRUNCATE_KEEP: Final = 0.6
"""Kesilgandan keyin qoladigan ulush — oxirgi ~40 % yo'qoladi.

Sarlavha, kvantlash jadvallari va birinchi skanerlash qatorlari YAROQLI
bo'lib qoladi. Ya'ni `Image.open()` MUVAFFAQIYATLI bo'ladi va xato faqat
`load()` da chiqadi — `open()` bilan cheklangan filtr buzuq kadrni
yaroqli deb qabul qilardi.
"""

_HTML_ERROR_BODY: Final[bytes] = (
    b"<html>\n"
    b"<head><title>401 Unauthorized</title></head>\n"
    b"<body>\n"
    b"<h1>401 Unauthorized</h1>\n"
    b"<p>The requested URL requires authorization.</p>\n"
    b"</body>\n"
    b"</html>\n"
)

JPEG_CONTENT_TYPE: Final = "image/jpeg"
HTML_CONTENT_TYPE: Final = "text/html; charset=utf-8"

_BASE_JPEG_B64: Final = (
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAUDBAQEAwUEBAQFBQUGBwwIBwcHBw8LCwkMEQ8SEhEP"
    "ERETFhwXExQaFRERGCEYGh0dHx8fExciJCIeJBweHx7/2wBDAQUFBQcGBw4ICA4eFBEUHh4eHh4e"
    "Hh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh7/wAARCAC0AUADAREA"
    "AhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQA"
    "AAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3"
    "ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWm"
    "p6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEA"
    "AwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSEx"
    "BhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElK"
    "U1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3"
    "uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD0CgAo"
    "AKAPn+gD6AoAKACgAoA+f6APoCgD5/oA+gKAPn+gD6AoA+f6APoCgD5/oAKACgAoAKAPoCgAoA+f"
    "6ACgD6AoAKAPn+gAoAKAPoCgD5/oAKACgD6AoAKAPn+gAoA+gKACgAoAKACgD5/oA+gKACgAoAKA"
    "Pn+gD6AoA+f6APoCgD5/oA+gKAPn+gD6AoA+f6ACgAoAKACgD6AoAKAPn+gAoA+gKACgD5/oAKAC"
    "gD6AoA+f6ACgAoA+gKACgD5/oAKAPoCgAoAKACgAoA+f6APoCgAoAKACgD5/oA+gKAPn+gD6AoA+"
    "f6APoCgD5/oA+gKAPn+gAoAKACgAoA+gKACgD5/oAKAPoCgAoA+f6ACgAoA+gKAPn+gAoAKAPoCg"
    "AoA+f6ACgD6AoAKACgAoAKAPn+gD6AoAKACgAoA+f6APoCgD5/oA+gKAPn+gD6AoA+f6APoCgD5/"
    "oAKACgAoAKAPoCgAoA+f6ACgD6AoAKAPn+gAoAKAPoCgD5/oAKACgD6AoAKAPn+gAoA+gKACgAoA"
    "KACgD5/oA+gKACgAoAKAPn+gD6AoA+f6APoCgD5/oA+gKAPn+gD6AoA+f6ACgAoAKACgD6AoAKAP"
    "n+gAoA+gKACgD5/oAKACgD6AoA+f6ACgAoA+gKACgD5/oAKAPoCgAoAKACgAoA+f6APoCgAoAKAC"
    "gD5/oA+gKAPn+gD6AoA+f6APoCgD5/oA+gKAPn+gAoAKACgAoA+gKACgD5/oAKAPoCgAoA+f6ACg"
    "AoA+gKAPn+gAoAKAPoCgAoA+f6ACgD6AoAKACgAoAKAPn+gD6AoAKACgAoA+f6APoCgD5/oA+gKA"
    "Pn+gD6AoA+f6APoCgD5/oAKACgAoAKAPoCgAoA+f6ACgD6AoAKAPn+gAoAKAPoCgD5/oAKACgD6A"
    "oAKAPn+gAoA+gKACgAoAKACgD5/oA+gKACgAoAKAPn+gD6AoA+f6APoCgD5/oA+gKAPn+gD6AoA+"
    "f6ACgAoAKACgD6AoAKAPn+gAoA+gKACgD5/oAKACgD6AoA+f6ACgAoA+gKACgD5/oAKAPoCgAoAK"
    "ACgAoA+f6APoCgAoAKACgD5/oA+gKAPn+gD6AoA+f6APoCgD5/oA+gKAPn+gAoAKACgAoA+gKACg"
    "D5/oAKAPoCgAoA+f6ACgAoA+gKAPn+gAoAKAPoCgAoA+f6ACgD6AoAKACgAoAKAPn+gD6AoAKACg"
    "AoA+f6APoCgD5/oA+gKAPn+gD6AoA+f6APoCgD5/oAKACgAoAKAPoCgAoA+f6ACgD6AoAKAPn+gA"
    "oAKAPoCgD5/oAKACgD6AoAKAPn+gAoA+gKACgAoAKACgD5/oA+gKACgAoAKAPn+gD6AoA+f6APoC"
    "gD5/oA+gKAPn+gD6AoA+f6ACgAoAKACgD6AoAKAPn+gAoA+gKACgD5/oAKACgD6AoA+f6ACgAoA+"
    "gKACgD5/oAKAPoCgAoAKACgAoA+f6APoCgAoAKACgD5/oA+gKAPn+gD6AoA+f6APoCgD5/oA+gKA"
    "Pn+gAoAKACgAoA+gKACgD5/oAKAPoCgAoA+f6ACgAoA+gKAPn+gAoAKAPoCgAoA+f6ACgD6AoAKA"
    "CgAoAKAPn+gD6AoAKACgAoA+f6APoCgD5/oA+gKAPn+gD6AoA+f6APoCgD5/oAKACgAoAKAPoCgA"
    "oA+f6ACgD6AoAKAPn+gAoAKAPoCgD5/oAKACgD6AoAKAPn+gAoA+gKACgAoAKACgD5/oA+gKACgA"
    "oAKAPn+gD6AoA+f6APoCgD5/oA+gKAPn+gD6AoA+f6ACgAoAKACgD6AoAKAPn+gAoA+gKACgD5/o"
    "AKACgD6AoA+f6ACgAoA+gKACgD5/oAKAPoCgAoAKACgAoA+f6APoCgAoAKACgD5/oA+gKAPn+gD6"
    "AoA+f6APoCgD5/oA+gKAPn+gAoAKACgAoA+gKACgD5/oAKAPoCgAoA+f6ACgAoA+gKAPn+gAoAKA"
    "PoCgAoA+f6ACgD6AoAKACgAoAKAPn+gD6AoAKACgAoA+f6APoCgD5/oA+gKAPn+gD6AoA+f6APoC"
    "gD5/oAKACgAoAKAPoCgAoA+f6ACgD6AoAKAPn+gAoAKAPoCgD5/oAKACgD6AoAKAPn+gAoA+gKAC"
    "gAoAKACgD5/oA+gKACgAoAKAPn+gD6AoA+f6APoCgD5/oA+gKAPn+gD6AoA+f6ACgAoAKACgD6Ao"
    "AKAPn+gAoA+gKACgD5/oAKACgD6AoA+f6ACgAoA+gKACgD5/oAKAPoCgAoAKACgAoA+f6APoCgAo"
    "AKACgD5/oA+gKAPn+gD6AoA+f6APoCgD5/oA+gKAPn+gAoAKACgAoA+gKACgD5/oAKAPoCgAoA+f"
    "6ACgAoA+gKAPn+gAoAKAPoCgAoA+f6ACgD6AoAKACgAoAKAPn+gD6AoAKACgAoA+f6APoCgD5/oA"
    "+gKAPn+gD6AoA+f6APoCgD5/oAKACgAoAKAPoCgAoA+f6ACgD6AoAKAPn+gAoAKAPoCgD5/oAKAC"
    "gD6AoAKAPn+gAoA+gKACgAoAKACgD5/oA+gKACgAoAKAPn+gD6AoA+f6APoCgD5/oA+gKAPn+gD6"
    "AoA+f6ACgAoAKACgD6AoAKAPn+gAoA+gKACgD5/oAKACgD6AoA+f6ACgAoA+gKACgD5/oAKAPoCg"
    "AoAKACgAoA+f6APoCgAoAKACgD5/oA+gKAPn+gD6AoA+f6APoCgD5/oA+gKAPn+gAoAKACgAoA+g"
    "KACgD5/oAKAPoCgAoA+f6ACgAoA+gKAPn+gAoAKAPoCgAoA+f6ACgD6AoAKACgAoAKAPn+gD6AoA"
    "KACgAoA+f6APoCgD5/oA+gKAPn+gD6AoA+f6APoCgD5/oAKACgAoAKAPoCgAoA+f6ACgD6AoAKAP"
    "n+gAoAKAPoCgD5/oAKACgD6AoAKAPn+gAoA+gKACgAoAKACgD5/oA+gKACgAoAKAPn+gD6AoA+f6"
    "APoCgD5/oA+gKAPn+gD6AoA+f6ACgAoAKACgD6AoAKAPn+gAoA+gKACgD5/oAKACgD6AoA+f6ACg"
    "AoA+gKACgD5/oAKAPoCgAoA//9k="
)

_BASE_JPEG: Final[bytes] = base64.b64decode(_BASE_JPEG_B64)

_TRUNCATED_JPEG: Final[bytes] = _BASE_JPEG[: int(len(_BASE_JPEG) * _TRUNCATE_KEEP)]

_BY_MODE: Final[dict[str, tuple[bytes, str]]] = {
    "ok": (_BASE_JPEG, JPEG_CONTENT_TYPE),
    "truncated": (_TRUNCATED_JPEG, JPEG_CONTENT_TYPE),
    # ⚠ `text/html` E'LON QILINADI, lekin bu HIMOYA EMAS. Real yo'lda
    #   proxy yoki firmware sarlavhani `image/jpeg` qoldirib yuborishi
    #   mumkin, ya'ni `Content-Type` ga ishonadigan filtr HTML sahifani
    #   YAROQLI KADR deb qabul qilardi (T-04-10). Sim sarlavhani TO'G'RI
    #   beradi — filtr baribir MAGIC BAYTGA qarashi shart va shu talab
    #   04-04 da testga aylanadi.
    "html": (_HTML_ERROR_BODY, HTML_CONTENT_TYPE),
    # ⚠ Bo'sh tana `image/jpeg` bilan keladi — aynan eng yomon shakl:
    #   sarlavha «bu kadr» deydi, tanada esa hech nima yo'q.
    "empty": (b"", JPEG_CONTENT_TYPE),
}


class UnknownFrameMode(ValueError):
    """`frame_mode` reyestrda yo'q — JIMGINA `ok` ga tushib ketmaydi."""


def frame_bytes_for_mode(mode: str) -> tuple[bytes, str]:
    """`(baytlar, Content-Type)` — `SimState.frame_mode` bo'yicha.

    Noma'lum rejim `UnknownFrameMode` beradi. Standart qiymatga jimgina
    qaytish eng qimmat turdagi yolg'on-yashil bo'lardi: test «buzuq kadr
    so'radim» deb o'ylab, aslida YAROQLI kadr ustida ishlab, sifat filtri
    umuman sinalmagan holda yashil qolardi.
    """
    try:
        return _BY_MODE[mode]
    except KeyError:
        raise UnknownFrameMode(
            f"noma'lum frame_mode={mode!r}; ruxsat etilganlar: {sorted(FRAME_MODES)}"
        ) from None
