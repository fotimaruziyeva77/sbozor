"""Shipped nginx konfiguratsiyasi — `include` bilan BIRGA o'qiladi.

=============================================================================
⛔⛔ NEGA BU FAYL BOR (260818, sakkizta darvoza ko'r bo'lib qolgandan keyin).

`ops/nginx/app.inc` ilova marshrutlarini `nginx.conf` dan CHIQARDI (sabab:
dev va production bitta manbadan o'qisin, aks holda birida tuzatilgan
xavfsizlik xatosi ikkinchisida jimgina qolardi).

O'sha refaktoring **sakkizta xavfsizlik darvozasini** jimgina ko'r qildi —
ular hammasi `nginx.conf` ni O'QIB qoidani u yerda qidirardi:

  * `test_rate_limit_proxy.py` — 3 ta: `X-Forwarded-For` OVERWRITE qoidasi;
  * `test_go2rtc_client.py`   — 5 ta: go2rtc API taqiqi (GHSA-wwww-5h25-jf98,
    CVSS 9.1) va `auth_request` nishoni.

Ikkalasi ham QIZARDI va bu OMAD edi: ular `assert` bilan yozilgan. Lekin
naqsh takrorlanardi — uchinchi fayl ham `NGINX_CONF.read_text()` yozib,
o'sha teshikka tushardi.

⛔ Shuning uchun o'qish YAGONA joyga chiqarildi. Yangi darvoza yozayotgan
   ijrochi `nginx.conf` ni to'g'ridan-to'g'ri o'qimaydi — u shu yerdan
   `effective_nginx_conf()` ni chaqiradi va qoida qayerda yotganidan
   QAT'I NAZAR uni ko'radi.
=============================================================================
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

# Repo ildizi: bu fayl `<root>/tests/fixtures/` da yotadi. Konteynerda ham
# (`working_dir: /app`, `.:/app`), xostda ham bir xil ishlaydi.
REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
NGINX_DIR: Final[Path] = REPO_ROOT / "ops" / "nginx"
NGINX_CONF: Final[Path] = NGINX_DIR / "nginx.conf"

_INCLUDE: Final[re.Pattern[str]] = re.compile(r"^\s*include\s+(?P<path>\S+);", re.MULTILINE)


def effective_nginx_conf() -> str:
    """`nginx.conf` + u `include` qilgan fayllar — BITTA matn.

    ⚠ Faqat REPO ICHIDAGI fayllar qo'shiladi: `include` qiymati
      konteyner yo'li bo'lishi mumkin (`/etc/nginx/app.inc`), shuning
      uchun undan faqat FAYL NOMI olinadi va u `ops/nginx/` da
      qidiriladi — compose uni aynan shu fayldan mount qiladi.

    ⚠ Izohlar TASHLANMAYDI: chaqiruvchilarning ba'zisi izohdagi
      tushuntirishni ham tekshiradi. Izoh muhim bo'lgan joyda
      chaqiruvchi o'zi filtrlaydi (`test_rate_limit_proxy.py` naqshi).
    """
    parts = [NGINX_CONF.read_text(encoding="utf-8")]

    for match in _INCLUDE.finditer(parts[0]):
        candidate = NGINX_DIR / Path(match.group("path")).name
        if candidate.is_file():
            parts.append(candidate.read_text(encoding="utf-8"))

    return "\n".join(parts)
