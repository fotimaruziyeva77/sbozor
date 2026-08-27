"""O'LIK `SIM_*` KONFIGURATSIYASINING DARVOZASI (CAM-09, 03-VERIFICATION GAP-1).

=============================================================================
NEGA BU DARVOZA BOR.

`03-VERIFICATION.md` `compose.yaml` dagi `SIM_RTSP_HOST: go2rtc-sim` qatorini
shunday nomladi:

    «RTSP oyog'ini ulash NIYAT QILINGAN, LEKIN BAJARILMAGAN ekanining
     mexanik izi»

Kalit bor edi, uni hech kim o'qimasdi, va bu holat oylar davomida jimgina
turdi: hech qanday test qizarmaydi, hech qanday linter shikoyat qilmaydi,
konteyner muvaffaqiyatli ko'tariladi. O'lik muhit o'zgaruvchisi — NIYAT bilan
BAJARILGAN ISH orasidagi farqning eng arzon va eng ishonchli izi, va u faqat
odam butun reponi o'qib chiqqanda ko'rinardi.

Bu fayl o'sha o'qishni CI'ga o'tkazadi.

=============================================================================
SKANERNING IKKI QOIDASI (03-01 da o'rnatilgan naqsh).

1. **QUYI CHEGARA MAJBURIY.** Yo'l noto'g'ri yozilganda yoki `compose.yaml`
   ko'chirilganda skaner BO'SH to'plamda ishlab, hamma assert jimgina o'tib
   ketardi — darvoza mavjudligini yo'qotgan holda yashil bo'lib turaverardi.

2. **SKANER O'Z FAYLINI ISTE'MOLCHILAR TO'PLAMIDAN CHIQARIB TASHLAYDI.**
   Aks holda darvoza O'ZINI O'ZI qanoatlantirardi: bu faylda eslatilgan har
   qanday o'lik kalit «iste'mol qilingan» ko'rinardi, ya'ni regressiya testi
   regressiyani YASHIRARDI.

`tests/unit/test_no_sim_branching.py` bilan aralashtirmang: u ILOVA KODIDA
sim satrini QIDIRADI (topilsa — yomon). Bu fayl teskari savol beradi —
compose'dagi sim kalitining ISTE'MOLCHISI BORMI (yo'q bo'lsa — yomon).
=============================================================================
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPOSE = REPO_ROOT / "compose.yaml"
MEDIAMTX_CONF = REPO_ROOT / "ops" / "mediamtx" / "mediamtx.yml"

CONSUMER_ROOTS = ("services/nvr-sim", "tests", "ops")
"""Sim kalitini o'qishi MUMKIN bo'lgan yagona uch daraxt.

`services/core-api/app/` ATAYIN YO'Q: u yerda `SIM_` uchrashi
`test_no_sim_branching.py` uchun XATO (ilova kodida sim tarmoqlanishi
bo'lmaydi). Ikki darvoza bir-biriga zid emas — ular turli daraxtlarga
qaraydi.
"""

CONSUMER_SUFFIXES = (".py", ".yaml", ".yml", ".json", ".sh", ".md", ".conf", ".toml")

SIM_KEY_RE = re.compile(r"\bSIM_[A-Z0-9_]+\b")
"""`SIM_RTSP_HOST: go2rtc-sim` ham, `${SIM_USERNAME:-admin}` ham bir xil tutiladi."""

MIN_SIM_KEYS = 4
"""Quyi chegara — yuqoridagi 1-qoida.

Bugungi to'plam AYNAN shu to'rttadan iborat: `SIM_CHANNEL_COUNT`,
`SIM_RTSP_PORT_ADVERTISED`, `SIM_USERNAME`, `SIM_PASSWORD`. Kalit
qo'shilsa chegara qayta ko'rib chiqilmaydi (u pastki chegara), kalit
YO'QOLSA esa bu assert darhol qizaradi va sabab ko'rinadi.
"""

REMOVED_KEYS = ("SIM_RTSP_HOST", "SIM_RTSP_PORT:")
"""03-12 da OLIB TASHLANGAN kalitlar — regressiya to'sig'i.

⚠ `SIM_RTSP_PORT` IKKI NUQTA bilan yozilgan: `SIM_RTSP_PORT_ADVERTISED`
  bu naqshga TUSHMASLIGI kerak, chunki u tirik va `sim/state.py` uni o'qiydi.
  Ikki nuqtasiz naqsh ikkalasini ham tutib, darvozani yolg'on-qizil qilardi.

⚠ Bu nomlar SHU FAYLNING O'ZIDA bor va bu muammo emas: skaner
  `compose.yaml` ni o'qiydi, o'zini emas.
"""


def _strip_comments(text: str) -> list[str]:
    """FAQAT butun-qator izohlar tashlanadi.

    Qator oxiridagi izoh (`SIM_X: 1  # nega`) QOLDIRILADI: uni kesish uchun
    `#` ni satr ichida izlash kerak bo'lardi va u YAML qiymatidagi `#`
    belgisini ham kesib yuborardi. Butun-qator izoh esa bir ma'noli —
    `compose.yaml` ning o'lik kalitlar haqidagi TUSHUNTIRISHI aynan shu
    shaklda yozilgan va u darvozani qizartirmasligi kerak.
    """
    return [line for line in text.splitlines() if not line.lstrip().startswith("#")]


def _compose_code_lines() -> list[str]:
    return _strip_comments(COMPOSE.read_text(encoding="utf-8"))


def _sim_keys() -> list[str]:
    keys: set[str] = set()
    for line in _compose_code_lines():
        keys.update(SIM_KEY_RE.findall(line))
    return sorted(keys)


def _consumer_files() -> list[Path]:
    """Iste'molchi bo'la oladigan fayllar — SKANERNING O'ZIDAN TASHQARI."""
    own = Path(__file__).resolve()
    files: list[Path] = []
    for root in CONSUMER_ROOTS:
        base = REPO_ROOT / root
        if not base.is_dir():
            continue
        files.extend(
            path
            for path in base.rglob("*")
            if path.is_file()
            and path.suffix in CONSUMER_SUFFIXES
            and path.resolve() != own
            and "node_modules" not in path.parts
        )
    return sorted(files)


SIM_KEYS = _sim_keys()
CONSUMERS = _consumer_files()


def test_scanner_actually_sees_the_compose_file() -> None:
    """QUYI CHEGARA: bo'sh to'plamda bu darvoza JIMGINA yashil bo'lardi."""
    assert COMPOSE.is_file(), f"`{COMPOSE}` topilmadi — yo'l eskirgan"
    assert len(SIM_KEYS) >= MIN_SIM_KEYS, (
        f"`compose.yaml` dan faqat {len(SIM_KEYS)} ta `SIM_*` kalit topildi "
        f"({SIM_KEYS}), kamida {MIN_SIM_KEYS} kutilgan. Skaner bo'sh to'plamda "
        "ishlayotgan bo'lsa quyidagi assert'lar hech nimani isbotlamaydi."
    )
    assert len(CONSUMERS) >= 50, (
        f"iste'molchi daraxtlarida faqat {len(CONSUMERS)} fayl topildi "
        f"({CONSUMER_ROOTS}) — yo'llar eskirgan bo'lsa har kalit «o'lik» "
        "ko'rinib, darvoza yolg'on-qizil bo'lardi"
    )


def test_every_compose_sim_key_has_a_consumer() -> None:
    """Har bir `SIM_*` kalitini KIMDIR o'qiydi — aks holda u o'lik konfiguratsiya."""
    texts = {path: path.read_text(encoding="utf-8", errors="ignore") for path in CONSUMERS}

    dead: list[str] = []
    for key in SIM_KEYS:
        consumers = [
            path.relative_to(REPO_ROOT).as_posix() for path, text in texts.items() if key in text
        ]
        if not consumers:
            dead.append(key)

    assert not dead, (
        "`compose.yaml` da ISTE'MOLCHISI YO'Q `SIM_*` kalit(lar)i bor: "
        f"{dead}\n\nHech kim o'qimaydigan muhit o'zgaruvchisi — «niyat qilingan, "
        "lekin bajarilmagan» ishning mexanik izi (03-VERIFICATION GAP-1: "
        "`SIM_RTSP_HOST` aynan shu tarzda RTSP oyog'i hech qachon ulanmaganini "
        f"oshkor qildi). Kalitni o'chiring yoki uni {CONSUMER_ROOTS} ostida "
        "haqiqatan o'qing."
    )


def test_removed_rtsp_host_keys_do_not_come_back() -> None:
    """`SIM_RTSP_HOST` / `SIM_RTSP_PORT` QAYTMAYDI — to'g'ri modelda ular yo'q.

    RTSP NVR'ning O'Z manzilida turadi (`nvr-sim-rtsp` xizmati,
    `network_mode: service:nvr-sim`), ya'ni «alohida RTSP xosti» degan
    tushunchaning o'zi noto'g'ri model edi. Bu test uni qaytib kelishidan
    to'sadi.
    """
    code = _compose_code_lines()
    for key in REMOVED_KEYS:
        hits = [line.strip() for line in code if key in line]
        assert not hits, (
            f"`{key}` `compose.yaml` ning IZOHSIZ qismiga qaytdi: {hits}\n"
            "Real NVR'da ISAPI ham, RTSP ham bitta manzilda yashaydi — alohida "
            "RTSP xosti/porti kaliti kerak bo'lsa, avval `nvr-sim-rtsp` ning "
            "`network_mode` qarori qayta ko'rib chiqilishi kerak."
        )


def test_the_dead_frontend_api_base_url_key_does_not_come_back() -> None:
    """⛔ `NEXT_PUBLIC_API_BASE_URL` `compose.yaml` ga QAYTMAYDI (WR-14, 08-11).

    =========================================================================
    NEGA BU DARVOZA SHU FAYLDA.

    Bu faylning butun mavzusi — «niyat qilingan, lekin bajarilmagan
    ishning mexanik izi» sifatidagi O'LIK MUHIT KALITI. `SIM_RTSP_HOST`
    va bu kalit AYNI sinfdan, faqat mexanizmi boshqacha: `NEXT_PUBLIC_*`
    Next.js da BUILD paytida bandlga inline qilinadi, ya'ni runtime
    `environment` qiymati ishga tushgan konteynerga yetib boradi-yu,
    allaqachon qadalgan qiymatni O'ZGARTIRA OLMAYDI.

    Nosozlik shakli o'sha eng yomon sinfdan: operator qiymatni
    o'zgartiradi, konteyner muvaffaqiyatli ko'tariladi, hech nima
    qizarmaydi — va frontend eski manzilga boradi.

    =========================================================================
    ⛔ KALIT `build.args` BILAN «TIRILTIRILMAYDI» — VA BU HAM QARORNING
       QISMI. `08-UI-SPEC.md` M-9: core-api'da `CORSMiddleware` UMUMAN
       YO'Q va refresh cookie'si `SameSite=Lax` (T-01-61), ya'ni boshqa
       origin qo'yilishi bilan AVTORIZATSIYANING O'ZI yiqiladi.
       Ishlaydigan tugma qilib qo'yish o'lik kalitni ishlaydigan TUZOQQA
       aylantirardi.

    ⚠ Kalit nomi SHU FAYLNING O'ZIDA bor va bu muammo emas: skaner
      `compose.yaml` ni o'qiydi, o'zini emas (yuqoridagi 2-qoida).
    """
    code = _compose_code_lines()
    hits = [line.strip() for line in code if "NEXT_PUBLIC_API_BASE_URL" in line]

    assert not hits, (
        f"`NEXT_PUBLIC_API_BASE_URL` `compose.yaml` ning IZOHSIZ qismiga qaytdi: "
        f"{hits}\n\n`NEXT_PUBLIC_*` BUILD paytida inline qilinadi, ya'ni runtime "
        "kaliti JIMGINA e'tiborsiz qolardi. Qiymat haqiqatan sozlanadigan "
        "bo'lishi kerak bo'lsa u `build.args` ga o'tishi SHART — lekin avval "
        "CORS (core-api'da `CORSMiddleware` yo'q) va `SameSite=Lax` refresh "
        "cookie'si qayta ko'rib chiqilsin, aks holda boshqa origin "
        "avtorizatsiyani butunlay yiqitadi (08-UI-SPEC M-9)."
    )


def test_the_frontend_service_block_is_still_scanned() -> None:
    """⛔ NAZORAT — usiz yuqoridagi test BO'SH-ROST bo'lardi.

    `frontend` bloki `compose.yaml` dan ko'chirilsa (yoki nomi
    o'zgarsa) «kalit yo'q» da'vosi MAZMUNIDAN QAT'I NAZAR yashil
    bo'lardi: yo'q blokda hech qanday kalit bo'lmaydi.
    """
    code = _compose_code_lines()
    assert any(line.strip() == "frontend:" for line in code), (
        "`compose.yaml` da `frontend` servisi topilmadi — yuqoridagi "
        "regressiya to'sig'i endi hech nimani o'lchamaydi"
    )


def test_sim_password_matches_between_compose_and_rtsp_config() -> None:
    """`SIM_PASSWORD` ning standart qiymati MediaMTX rekviziti bilan bir xil.

    Ikki manba ajralib ketsa nosozlik shakli o'ta yomon bo'lardi: kashfiyot
    bazaga TO'G'RI parolni yozadi, go2rtc uni to'g'ri uzatadi, RTSP server
    esa baribir `401` beradi — va sabab «kod buzilgan» bo'lib ko'rinardi.

    ⚠ Bu test STANDART qiymatlarni solishtiradi. `.env` orqali ikkalasini
      birdan almashtirish yo'li yo'q va bu ataylab: sim rekviziti sir emas,
      u test uskunasining qismi.
    """
    compose_defaults = set(
        re.findall(
            r"SIM_PASSWORD:\s*\"\$\{SIM_PASSWORD:-([^}\"]+)\}\"",
            COMPOSE.read_text(encoding="utf-8"),
        )
    )
    assert compose_defaults, (
        '`compose.yaml` da `SIM_PASSWORD: "${SIM_PASSWORD:-...}"` shakli topilmadi — '
        "shakl o'zgargan bo'lsa bu darvoza ham yangilanishi kerak"
    )
    assert len(compose_defaults) == 1, (
        f"`SIM_PASSWORD` ning standart qiymati compose ICHIDA ajralib ketdi: "
        f"{sorted(compose_defaults)} (`nvr-sim` va `tests` bloklari)"
    )

    # `[ \t]` — `\s` EMAS: `\s` yangi qatorni ham yeydi va bo'sh `pass:` dan
    # keyingi qatorni qiymat deb olib ketardi (anonim yozuvlarning `pass:` i
    # ATAYIN bo'sh).
    mediamtx_passwords = re.findall(
        r"^[ \t]*pass:[ \t]+(\S+)[ \t]*$",
        MEDIAMTX_CONF.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    assert len(mediamtx_passwords) == 1, (
        f"`{MEDIAMTX_CONF.name}` da AYNAN bitta qiymatli `pass:` kutilgan, "
        f"topilgani: {mediamtx_passwords}. Anonim yozuvlarning `pass:` i bo'sh "
        "bo'lishi shart — parolli anonim yozuv rekvizit talabini bekor qilardi."
    )

    assert mediamtx_passwords[0] == compose_defaults.pop(), (
        f"parol ikki joyda AJRALIB KETDI: MediaMTX `{mediamtx_passwords[0]}`, "
        "compose'dagi `SIM_PASSWORD` standarti boshqa"
    )


# =============================================================================
# 4-FAZA (W0-10): MediaMTX SIFAT-YO'LLARINING IKKI DARVOZASI.
#
# `mediamtx.yml` ga qorong'i / kulrang / past-kontrastli oqim yo'llari
# qo'shildi. Ular ikki narsani JIMGINA buzishi mumkin va ikkalasi ham
# faqat ODAM o'qiganda ko'rinardi — shuning uchun ikkalasi ham shu yerda
# mexanik tekshiriladi.
# =============================================================================

_PATH_KEY_RE = re.compile(r'^  "([^"]+)":', re.MULTILINE)
"""`paths:` bo'limidagi yo'l kalitlari — FAYLDAGI TARTIBDA.

⚠ YAML PARSERI ATAYIN ISHLATILMAYDI: bu yerdagi savol qiymatlar haqida
  emas, ularning TARTIBI haqida, va tartib matn darajasidagi xususiyat.
  Parser bu faylni lug'atga aylantirib, keyingi o'quvchida «tartib
  ahamiyatsiz» degan noto'g'ri taassurot qoldirardi. Ikkinchi sabab
  amaliy: `pyyaml` bu repoda bog'liqlik EMAS va faqat shu test uchun
  paket qo'shish T-04-SC ga zid bo'lardi.
"""

_QUALITY_PATH_MARKER = "900[12]"
"""Sifat-ssenariylarining BIRINCHISI (qorong'i kadr, kanal 90)."""

_CATCH_ALL_MARKER = "[0-9]+"
"""Umumiy yo'lning ajratuvchi belgisi.

⚠ To'liq regex SHU YERDA TAKRORLANMAYDI va u `mediamtx.yml` ning
  IZOHIDA ham takrorlanmaydi: skaner faylni MATN sifatida o'qiydi va
  birinchi uchrashuvni oladi, ya'ni izohdagi nusxa darvozani
  yolg'on-qizil qilardi (`nvr-copy.test.mjs` dagi bilan bir xil sinf).
"""


def test_quality_paths_precede_the_catch_all_path() -> None:
    """Sifat-yo'llari umumiy yo'ldan OLDIN turadi — aks holda ular O'LIK.

    MediaMTX yo'llarni E'LON TARTIBIDA sinaydi va birinchi mos kelganini
    oladi. Umumiy regex barcha raqamli kanallarni qamraydi, ya'ni u
    yuqorida tursa 90xx/91xx/92xx ni ham yutib yuborardi va sifat
    ssenariylari JIMGINA oddiy `testsrc2` oqimini berardi.

    ⚠ NOSOZLIK SHAKLI ENG YOMONI: hech nima yiqilmaydi. Oqim ochiladi,
      kadr keladi, sifat filtri «yaroqli» deydi — va CAM-06 ning butun
      isboti o'z-o'ziga qaytadi.
    """
    keys = _PATH_KEY_RE.findall(MEDIAMTX_CONF.read_text(encoding="utf-8"))

    # QUYI CHEGARA (03-01 naqshi): kalitlar o'qilmasa quyidagi assert
    # bo'sh ro'yxatda jimgina o'tib ketardi.
    assert len(keys) >= 4, (
        f"`{MEDIAMTX_CONF.name}` dan atigi {len(keys)} yo'l kaliti o'qildi ({keys}) — "
        "kutilgan >= 4 (uchta sifat-ssenariysi + umumiy yo'l). Kalit shakli "
        "o'zgargan bo'lsa bu darvoza ham yangilanishi kerak."
    )

    quality = [index for index, key in enumerate(keys) if _QUALITY_PATH_MARKER in key]
    catch_all = [index for index, key in enumerate(keys) if _CATCH_ALL_MARKER in key]

    assert quality, f"sifat-ssenariysi yo'li topilmadi ({_QUALITY_PATH_MARKER}): {keys}"
    assert catch_all, f"umumiy yo'l topilmadi: {keys}"
    assert max(quality) < min(catch_all), (
        f"sifat-yo'llari umumiy yo'ldan KEYIN turibdi: {keys}. MediaMTX birinchi "
        "mos kelgan yo'lni oladi, ya'ni bu tartibda ular hech qachon ishga tushmaydi."
    )


def test_quality_paths_did_not_add_a_new_credential() -> None:
    """Yangi yo'l yangi rekvizit QO'SHMAYDI (T-04-13).

    Mavjud `admin` yozuvi barcha yo'llarni qamraydi (`permissions` yo'lga
    bog'lanmagan). Yangi rekvizit `compose.yaml` dagi `SIM_PASSWORD` bilan
    IKKINCHI haqiqat manbai tug'dirardi va ajralib ketganda go2rtc to'g'ri
    parol yuborib ham `401` olardi.

    ⚠ `[ \\t]` — `\\s` EMAS. Yuqoridagi test bilan bir xil sabab: `\\s`
      yangi qatorni ham yeydi va bo'sh `pass:` dan keyingi qatorni qiymat
      deb olib ketadi (anonim yozuvlarning `pass:` i ATAYIN bo'sh).
      `\\s` bilan yozilgan tekshiruv bu faylda AVVALDAN 3 natija berardi,
      ya'ni u hech qachon o'ta olmasdi.
    """
    text = MEDIAMTX_CONF.read_text(encoding="utf-8")

    users = re.findall(r"^  - user:\s*(\S+)\s*$", text, re.MULTILINE)
    assert len(users) == 3, (
        f"`authInternalUsers` yozuvlari soni {len(users)} ({users}), kutilgan 3: "
        "anonim-huquqsiz, `admin`-o'qish, loopback-publish. Yangi yozuv qo'shilgan "
        "bo'lsa avval T-04-13 qayta ko'rib chiqilishi kerak."
    )

    valued = re.findall(r"^[ \t]*pass:[ \t]+(\S+)[ \t]*$", text, re.MULTILINE)
    assert len(valued) == 1, (
        f"qiymatli `pass:` qatorlari: {valued}. Aynan bittasi bo'lishi SHART — "
        "u `compose.yaml` dagi `SIM_PASSWORD` standarti bilan solishtiriladi."
    )
