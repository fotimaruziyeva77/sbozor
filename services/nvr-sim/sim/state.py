"""`/__sim__/` control-plane — sim holati va xato rejimlari.

=============================================================================
NEGA `/__sim__/` PREFIKSI:
  1. U `/ISAPI/*` bilan **hech qachon** chalkashmaydi — ikki nomlar fazasi
     kesishmaydi, ya'ni "boshqaruv chaqiruvi qurilma chaqiruviga o'xshab
     ketdi" xatosi tuzilma darajasida mumkin emas.
  2. Prodda bunday yo'l **umuman mavjud emas**: sim konteyneri `--profile sim`
     ortida va prod deploy profilsiz ishlaydi.
  3. Control-plane **Digest talab qilmaydi** — u test boshqaruvi, qurilma
     yuzasi emas. Digest ortiga yashirish testni sim'ning o'z auth mantig'iga
     bog'lab qo'yardi (auth buzilsa holatni tiklab ham bo'lmasdi).
=============================================================================

Holat **jarayon xotirasida** yashaydi: sim bitta ishchi bilan ishlaydi va
`uvicorn` ga `--workers` berilmaydi (compose.yaml). Ikkinchi ishchi bo'lsa
`POST /__sim__/state` ishchilarning faqat bittasiga tegardi va testlar
tushunarsiz tarzda "gohida" yiqilardi.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from .frames import FRAME_MODES

MODEL_DS_7616 = "DS-7616NI-K2"
MODEL_DS_7732 = "DS-7732NI-M4"
MODEL_IPCAMERA = "DS-2CD2346G2-ISU"

KNOWN_MODELS: frozenset[str] = frozenset({MODEL_DS_7616, MODEL_DS_7732, MODEL_IPCAMERA})
"""`model` — bu FIXTURE TANLAGICHI, javobdagi `<model>` qiymati emas.

Javobdagi `<model>` fixture'dan VERBATIM keladi (masalan IP-kamera uchun
`DS-2CD2346G2-ISU/SL` — dumpdagi to'liq nom). Bu yerdagi kalit esa fayl
nomiga mos keladi. Ikkalasini ajratish ataylab: fayl nomida `/` bo'lmaydi,
qurilma esa modelini xohlagancha yozadi.

Noma'lum model `400` beradi, `500` emas — aks holda test "fixture yo'q"
xatosini "sim yiqildi" deb ko'rardi.
"""

DEFAULT_STREAM_LIMIT = 128
"""Hikvision hujjatlashtirgan "maximum number of streams" (A.5) — modelga qarab o'zgaradi.

Standart qiymat sifatida aynan shu olindi (0 = "cheksiz" degan sehrli qiymat
emas): qurilmada chegara HAR DOIM bor, va uni realistik son bilan modellash
"chegara yo'q" degan yolg'on taxminni kodga kiritmaydi. `stream_limit` testi
esa D-09 bo'yicha **4** bilan ishlaydi.
"""

STREAM_LIMIT_REJECT = "reject"
STREAM_LIMIT_SILENT = "silent"

SIM_MODES: frozenset[str] = frozenset(
    {
        "ok",
        "bad_password",
        "account_locked",
        "clock_drift",
        "digest_stale",
        "basic_only",
        "no_permission",
        "channel_offline",
        "channel_removed",
        "channel_added",
        "camera_swapped",
        "stream_limit",
        "slow",
        "isapi_404",
        "not_hikvision",
        "port_moved",
        "unreachable",
    }
)
"""`03-RESEARCH.md` B.8 jadvalidagi barcha rejimlar (`ok` + o'n oltita xato rejimi).

⚠ `unreachable` — YAGONA rejim, u `/__sim__/state` bilan O'RNATILMAYDI: uni
qayta tug'dirishning yagona haqiqiy yo'li konteynerni to'xtatish
(`docker compose stop nvr-sim`). Uni bu yerda ro'yxatda saqlash ataylab:
`POST /__sim__/state {"mode": "unreachable"}` **aniq xato** qaytaradi,
jimgina qabul qilib "hech nima qilmaydigan" rejim bo'lib qolmaydi.
"""

UNSETTABLE_MODES: frozenset[str] = frozenset({"unreachable"})

# ⚠ `frame_mode` ATAYIN `SIM_MODES` GA QO'SHILMADI — bu IKKINCHI O'LCHAM.
#
#   `mode`       — ULANISH va AUTENTIFIKATSIYA o'lchami: so'rov qurilma
#                  yuzasiga YETIB BORDIMI (`bad_password`, `clock_drift`,
#                  `unreachable`, …).
#   `frame_mode` — JAVOB BAYTLARI o'lchami: yetib borgan so'rov QANDAY
#                  tana oldi (`ok`, `truncated`, `html`, `empty`).
#
# Ikkalasini bitta enumga yig'ish «noto'g'ri parol VA buzuq kadr»
# kombinatsiyasini ifodalab bo'lmas qilardi. Holbuki 04-04 ning retry
# siyosati aynan shu ikkisini AJRATISHI shart: `401` da qayta urinish
# hisobni qulflaydi (D-03, ZARARLI), buzuq kadrda esa qayta urinish
# aynan TO'G'RI amal. Bitta o'lcham bo'lganda bu farqni sinab bo'lmasdi.
#
# `FRAME_MODES` ning O'ZI `sim/frames.py` da yashaydi — baytlar bilan
# birga, ya'ni yangi rejim qo'shilganda reyestr va uning tanasi
# ajralib ketmaydi.


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass
class SimState:
    """Sim'ning butun kuzatiladigan xulqi shu yerdan boshqariladi."""

    mode: str = "ok"
    frame_mode: str = "ok"
    """`/picture` javobining BAYTLARI — yuqoridagi izohdagi ikkinchi o'lcham.

    Standart `"ok"`: `POST /__sim__/reset` shu qiymatga qaytaradi, ya'ni
    buzuq kadr keyingi testga SIZIB O'TMAYDI.
    """
    model: str = MODEL_DS_7616
    channel_count: int = 6
    rtsp_port: int = 554
    drift_seconds: int = 0
    offline_channels: set[int] = field(default_factory=set)
    removed_channels: set[int] = field(default_factory=set)
    no_substream_channels: set[int] = field(default_factory=set)
    delay_ms: int = 0
    stream_limit: int = DEFAULT_STREAM_LIMIT
    stream_limit_mode: str = STREAM_LIMIT_REJECT
    stream_claims: int = 0
    auth_attempts: int = 0
    endpoint_hits: dict[str, int] = field(default_factory=dict)
    """Qaysi `/ISAPI/*` yo'li NECHA MARTA chaqirildi — SANAGICH, sozlama emas.

    ⚠ NEGA BU KERAK: D-04 ning tarmoqlanishi («IP-kamerada `InputProxy`
      CHAQIRILMAYDI») ni natijadan o'lchab bo'lmaydi — `InputProxy` ni
      chaqirib, `404` ni yutib, keyin to'g'ri yo'ldan borgan kod ham
      AYNAN BIR XIL kamera yozuvlarini yaratardi. Ya'ni «chaqirilmadi»
      da'vosining yagona dalili — so'rovlar sanog'i.

    Nima uchun bu qurilma fidelity'sini buzmaydi: sanoq FAQAT
    `/__sim__/state` da ko'rinadi, ISAPI javoblariga umuman ta'sir
    qilmaydi. Real qurilma ham so'rovlarni sanaydi (jurnalida), biz esa
    o'sha jurnalning test uchun o'qiladigan shaklini beramiz.
    """

    # `camera_swapped` rejimi uchun (B.8): kanalning manba kamerasi almashtirildi.
    swapped_channel: int | None = None
    swapped_ip: str | None = None
    swapped_model: str | None = None

    @classmethod
    def from_env(cls) -> SimState:
        """Muhitdagi standart holat — `POST /__sim__/reset` aynan shunga qaytaradi."""
        return cls(
            channel_count=_env_int("SIM_CHANNEL_COUNT", 6),
            rtsp_port=_env_int("SIM_RTSP_PORT_ADVERTISED", 554),
            model=os.environ.get("SIM_MODEL", MODEL_DS_7616),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "frame_mode": self.frame_mode,
            "model": self.model,
            "channel_count": self.channel_count,
            "rtsp_port": self.rtsp_port,
            "drift_seconds": self.drift_seconds,
            "offline_channels": sorted(self.offline_channels),
            "removed_channels": sorted(self.removed_channels),
            "no_substream_channels": sorted(self.no_substream_channels),
            "delay_ms": self.delay_ms,
            "stream_limit": self.stream_limit,
            "stream_limit_mode": self.stream_limit_mode,
            "stream_claims": self.stream_claims,
            "auth_attempts": self.auth_attempts,
            # Nusxa: chaqiruvchi qaytgan lug'atni o'zgartirsa sanoq
            # buzilardi va sabab test kodida ko'rinmasdi.
            "endpoint_hits": dict(self.endpoint_hits),
            "swapped_channel": self.swapped_channel,
            "swapped_ip": self.swapped_ip,
            "swapped_model": self.swapped_model,
        }


_INT_FIELDS = ("channel_count", "rtsp_port", "drift_seconds", "delay_ms", "stream_limit")
_SET_FIELDS = ("offline_channels", "removed_channels", "no_substream_channels")
_OPTIONAL_INT_FIELDS = ("swapped_channel",)
_OPTIONAL_STR_FIELDS = ("swapped_ip", "swapped_model")

READ_ONLY_FIELDS: frozenset[str] = frozenset({"stream_claims", "auth_attempts", "endpoint_hits"})
"""SANAGICHLAR — tashqaridan o'rnatilmaydi.

Aks holda test o'zi o'lchayotgan qiymatni o'zi yozib qo'yardi. Ularni nolga
qaytarishning yagona yo'li — `POST /__sim__/reset`.
"""

PATCHABLE_FIELDS: frozenset[str] = frozenset(
    {"mode", "frame_mode", "model", "stream_limit_mode", *_INT_FIELDS, *_SET_FIELDS}
    | set(_OPTIONAL_INT_FIELDS)
    | set(_OPTIONAL_STR_FIELDS)
)


class SimStateError(ValueError):
    """Control-plane so'rovi yaroqsiz — `400` bilan qaytariladi."""


def apply_patch(state: SimState, patch: dict[str, Any]) -> SimState:
    """`POST /__sim__/state` — **QISMAN** yangilash: berilmagan maydon tegilmaydi.

    Noma'lum kalit **jimgina tashlab yuborilmaydi**: test "men rejimni
    o'rnatdim" deb o'ylab, aslida hech nima o'zgarmagan holatda ishlashi —
    aynan shu fazada eng qimmat turdagi yolg'on-yashil bo'lardi.
    """
    read_only = set(patch) & READ_ONLY_FIELDS
    if read_only:
        raise SimStateError(
            f"{sorted(read_only)} — sanagich, tashqaridan o'rnatilmaydi; "
            "nolga qaytarish uchun `POST /__sim__/reset`"
        )
    unknown = set(patch) - PATCHABLE_FIELDS
    if unknown:
        raise SimStateError(f"noma'lum maydon(lar): {sorted(unknown)}")

    if "mode" in patch:
        mode = str(patch["mode"])
        if mode not in SIM_MODES:
            raise SimStateError(f"noma'lum mode={mode!r}; ruxsat etilganlar: {sorted(SIM_MODES)}")
        if mode in UNSETTABLE_MODES:
            raise SimStateError(
                f"mode={mode!r} `/__sim__/state` bilan o'rnatilmaydi — uni qayta "
                "tug'dirishning yagona haqiqiy yo'li konteynerni to'xtatish: "
                "`docker compose stop nvr-sim`"
            )
        state.mode = mode

    if "frame_mode" in patch:
        # NOMA'LUM QIYMAT — noma'lum KALIT bilan bir xil mulohaza (yuqoridagi
        # docstring): test "buzuq kadr rejimini o'rnatdim" deb o'ylab, aslida
        # YAROQLI kadr ustida ishlab, sifat filtri umuman sinalmagan holda
        # yashil qolishi — aynan shu fazadagi eng qimmat yolg'on-yashil.
        # Kalit tekshiruvi buni USHLAMAYDI: `frame_mode` PATCHABLE_FIELDS da
        # bor, ya'ni `{"frame_mode": "corrupt"}` kalit darvozasidan O'TADI.
        frame_mode = str(patch["frame_mode"])
        if frame_mode not in FRAME_MODES:
            raise SimStateError(
                f"noma'lum frame_mode={frame_mode!r}; ruxsat etilganlar: {sorted(FRAME_MODES)}"
            )
        state.frame_mode = frame_mode

    if "model" in patch:
        model = str(patch["model"])
        if model not in KNOWN_MODELS:
            raise SimStateError(
                f"noma'lum model={model!r}; fixture mavjudlari: {sorted(KNOWN_MODELS)}"
            )
        state.model = model

    if "stream_limit_mode" in patch:
        value = str(patch["stream_limit_mode"])
        if value not in {STREAM_LIMIT_REJECT, STREAM_LIMIT_SILENT}:
            raise SimStateError(
                f"stream_limit_mode={value!r} — faqat {STREAM_LIMIT_REJECT!r} yoki "
                f"{STREAM_LIMIT_SILENT!r} (D-05 ning ikkala stsenariysi)"
            )
        state.stream_limit_mode = value

    for name in _INT_FIELDS:
        if name in patch:
            setattr(state, name, int(patch[name]))

    for name in _SET_FIELDS:
        if name in patch:
            setattr(state, name, {int(x) for x in patch[name]})

    for name in _OPTIONAL_INT_FIELDS:
        if name in patch:
            raw = patch[name]
            setattr(state, name, None if raw is None else int(raw))

    for name in _OPTIONAL_STR_FIELDS:
        if name in patch:
            raw = patch[name]
            setattr(state, name, None if raw is None else str(raw))

    return state
