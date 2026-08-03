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
