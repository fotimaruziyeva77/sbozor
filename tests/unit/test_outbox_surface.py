"""⛔ G7-1 — dalil-kadr Telegram'ga CHIQA OLMASLIGINING strukturaviy darvozasi.

=============================================================================
QOIDA: RASM BIRIKTIRUVCHI BOT API METODI IKKALA MODULDA HAM YO'Q.

Taqiq `alerts.py` ning 1-taqig'ida to'liq yozilgan va u huquqiy:

  * dalil-kadrda bozor tashrifchilari va sotuvchilarning yuzlari bo'ladi,
    ya'ni u O'zR ning shaxsiy ma'lumotlar qonuni ostida;
  * Telegram serverlari loyiha zimmasiga olgan data-rezidentlik
    chegarasidan TASHQARIDA va bir marta yuborilgan baytni QAYTARIB
    BO'LMAYDI — o'chirilgan xabar ham serverlarda qolishi mumkin.

Ya'ni bu «xavfsizlik sozlamasi» emas: metod bir marta yozilsa, u yozilgan
kundan boshlab QAYTARIB BO'LMAYDIGAN sizish yo'li bo'lardi.
=============================================================================

=============================================================================
⛔ BU DARVOZA `test_alerting.py::test_sender_public_surface_did_not_grow` NI
   TAKRORLAMAYDI — U BILAN JUFTLASHADI.

| Darvoza | Nimani o'lchaydi | Nimani KO'RMAYDI |
|---------|------------------|------------------|
| `dir(AlertSender)` | SINF yuzasi o'sdimi | xom `httpx` chaqiruvi, `outbox.py` |
| bu fayl | ikki modul matnida taqiqlangan nom | boshqacha nomlangan metod |

Ikkinchi ustun aynan shu sababdan muhim: `outbox.py` `AlertSender` sinfiga
umuman tegmasdan `client.post(f"{base}/bot{token}/sendPhoto", ...)` yozishi
mumkin edi va SINF darvozasi buni KO'RMASDI.
=============================================================================

⛔ TAQIQLANGAN NOMLAR RO'YXATI SHU FAYLDA, MAHSULOTDAN IMPORT QILINMAYDI
   (05-15 darsi). Import darvozani o'zi tekshirayotgan qiymatga bog'lardi:
   mahsulotga uchinchi metod qo'shilsa ro'yxat u bilan BIRGA kengayardi va
   darvoza jimgina yashil qolardi.

⚠ NAZORAT BANDI MAJBURIY: bu darvoza loyihasi bo'yicha HAR DOIM yashil
  bo'lishi kerak, ya'ni «yashil» uning haqiqatan qidirayotganini
  ISBOTLAMAYDI. Shuning uchun predikat ATAYIN EKILGAN matn ustida alohida
  o'lchanadi (`test_forbidden_tokens_are_reachable`).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

SCANNED_MODULES: tuple[Path, ...] = (
    REPO_ROOT / "services" / "core-api" / "app" / "jobs" / "outbox.py",
    REPO_ROOT / "services" / "core-api" / "app" / "services" / "alerts.py",
)
"""⛔ IKKALA MODUL HAM SKANERLANADI.

`alerts.py` — Bot API bilan gaplashadigan YAGONA joy; `outbox.py` — uni
chaqiradigan va shuning uchun «bir marta o'zim yozib qo'ya qolay» vasvasasi
tug'iladigan joy. Bittasini tekshirish ikkinchisini ochiq qoldirardi.
"""

MIN_SCANNED_BYTES = 2_000
"""Skanerlanadigan har bir faylning QUYI CHEGARASI.

Usiz yo'l eskirganda (fayl ko'chirilsa yoki qayta nomlansa) skaner BO'SH
matnda ishlab, hamma «yo'q» da'vosi jimgina o'tib ketardi — darvoza o'z
mavjudligini yo'qotgan holda yashil bo'lib turaverardi. Bu 03-01 da
o'rnatilgan qoida (`test_no_sim_branching.py::MIN_SCANNED_FILES`).
"""

FORBIDDEN_BOT_API_TOKENS: tuple[str, ...] = (
    # --- Rasm/media/hujjat yuboradigan Bot API metodlari ---
    "sendPhoto",
    "sendDocument",
    "sendMediaGroup",
    "sendVideo",
    "sendAnimation",
    "sendAudio",
    "sendVoice",
    "sendSticker",
    "sendVideoNote",
    # --- Ularning argumentlari va tiplari ---
    "InputFile",
    "InputMedia",
    "photo=",
    "document=",
    "video=",
    "media=",
    # --- Fayl yuklashning HTTP shakli (`httpx` ning multipart yo'li) ---
    "files=",
    "multipart",
)
"""⛔ IKKALA MODULDA HAM UCHRAMASLIGI KERAK BO'LGAN SATRLAR.

⚠ RO'YXATDA FAQAT METOD NOMLARI EMAS, ARGUMENTLAR VA HTTP SHAKLI HAM BOR
  va bu ATAYIN: `sendPhoto` ni yozmasdan ham rasm yuborish mumkin —
  `client.post(url, files={...})` shakli o'sha ishni bajaradi va faqat
  metod nomlarini qidiradigan ro'yxat uni KO'RMASDI.

⚠ RO'YXAT MAHSULOTDAN IMPORT QILINMAYDI — modul docstringiga qarang.
"""

_URL_METHOD_PATTERN = re.compile(r"/bot\{[^{}]*\}/\{([A-Za-z_][A-Za-z0-9_]*)\}")
"""Bot API URL'i quriladigan joyning shakli: `.../bot{<sir>}/{<KONSTANTA>}`.

⛔ NAQSH METOD SEGMENTINI GURUHGA OLADI va test uning AYNAN
   `TELEGRAM_SEND_METHOD` konstantasi ekanini talab qiladi. Ya'ni URL'ga
   literal metod nomini yozish (`.../bot{token}/sendPhoto`) darvozadan
   IKKI YO'LDAN ushlanadi: literal ro'yxatdan va bu naqshdan.
"""


def _sources() -> dict[str, str]:
    """Skanerlanadigan modullarning matni (kalit — repo ichidagi yo'l)."""
    return {
        path.relative_to(REPO_ROOT).as_posix(): path.read_text(encoding="utf-8")
        for path in SCANNED_MODULES
    }


def _hits(token: str, label: str, source: str) -> list[str]:
    """Taqiqlangan satrni fayl va QATOR bilan topadi (xato xabari uchun)."""
    return [
        f"{label}:{lineno}: {line.strip()}"
        for lineno, line in enumerate(source.splitlines(), start=1)
        if token in line
    ]


SOURCES = _sources()


def test_the_scanned_modules_are_actually_read() -> None:
    """Quyi chegara: skaner bo'sh matnda ishlayotgan bo'lsa darvoza YO'Q."""
    for label, source in SOURCES.items():
        assert len(source) >= MIN_SCANNED_BYTES, (
            f"`{label}` faqat {len(source)} bayt — kamida {MIN_SCANNED_BYTES} "
            "kutilgan. Yo'l eskirgan yoki fayl ko'chirilgan bo'lsa bu darvoza "
            "BO'SH matnda yashil bo'lib turaverardi."
        )
    assert len(SOURCES) == len(SCANNED_MODULES), "skanerlanadigan modul YO'QOLDI"


@pytest.mark.parametrize("token", FORBIDDEN_BOT_API_TOKENS)
def test_no_media_bot_api_method_appears_in_scanned_modules(token: str) -> None:
    """⛔ G7-1 — rasm/hujjat yuboruvchi Bot API yuzasi ikkala modulda ham YO'Q."""
    hits = [line for label, source in SOURCES.items() for line in _hits(token, label, source)]

    assert not hits, (
        f"taqiqlangan Bot API satri {token!r} topildi:\n  "
        + "\n  ".join(hits)
        + "\n\nDalil-kadr — SHAXSIY MA'LUMOT, Telegram serverlari esa O'zR "
        "data-rezidentlik chegarasidan TASHQARIDA. Bir marta yuborilgan baytni "
        "QAYTARIB BO'LMAYDI, ya'ni bu metod «keyin o'chiramiz» deb qo'shiladigan "
        "qulaylik emas (D-03)."
    )


def test_telegram_send_method_is_the_only_bot_api_path() -> None:
    """⛔ Bot API URL'i AYNAN BITTA joyda quriladi va metod — KONSTANTA.

    =======================================================================
    ⛔ IKKI DA'VO BIR VAQTDA:

      1. URL quriladigan joy AYNAN BITTA. Ikkinchisi paydo bo'lsa ikkita
         sizish yuzasi bo'lardi va ulardan biri (ehtimol yangisi)
         darvozalarsiz qolardi.
      2. Metod segmenti — LITERAL emas, KONSTANTA (`TELEGRAM_SEND_METHOD`).
         Literal yozish yangi metodni ro'yxatga tushmagan nom bilan
         qo'shish yo'lini ochardi.

    ⚠ `outbox.py` DA URL UMUMAN QURILMAYDI: u jo'natuvchini CHAQIRADI,
      Telegram bilan o'zi gaplashmaydi. Nol talabi shuni qulflaydi.
    =======================================================================
    """
    matches = {label: _URL_METHOD_PATTERN.findall(source) for label, source in SOURCES.items()}

    alerts = next(found for label, found in matches.items() if label.endswith("alerts.py"))
    outbox = next(found for label, found in matches.items() if label.endswith("outbox.py"))

    assert len(alerts) == 1, (
        f"`alerts.py` da Bot API URL'i {len(alerts)} joyda quriladi (kutilgani 1): "
        f"{alerts}. Ikkinchi qurilish joyi ikkinchi sizish yuzasi degani."
    )
    assert alerts[0] == "TELEGRAM_SEND_METHOD", (
        f"URL'dagi metod segmenti konstanta emas: {alerts[0]!r}. Literal yozilgan "
        "metod nomi taqiqlangan ro'yxatdan CHETLAB o'tishi mumkin edi."
    )
    assert outbox == [], (
        f"`outbox.py` Telegram URL'ini O'ZI quryapti: {outbox}. Job jo'natuvchini "
        "CHAQIRADI — ikkinchi HTTP yo'li `alerts.py` ning uchala taqig'ini ham "
        "IKKILANTIRARDI."
    )


def test_the_message_id_accessor_is_module_level_not_a_sender_attribute() -> None:
    """⛔ `provider_message_id` uchun O'QISH YO'LI sinf yuzasini O'STIRMADI.

    =======================================================================
    ⛔ NEGA BU O'LCHANADI: `outbox_repo.mark_delivered()` Telegram bergan
       `message_id` ni TALAB QILADI, `send_message()` esa `bool` qaytaradi
       va uning kontrakti (3-taqiq) O'ZGARMAYDI. Qiymat shuning uchun
       modul darajasidagi `last_message_id()` funksiyasi orqali chiqadi.

    ⛔ DA'VO AYNAN SHU: bu YO'L `AlertSender` ga YANGI ATRIBUT
       QO'SHMAGAN. Aks holda `dir()` darvozasining literal to'plami
       jimgina beshinchi nomga kengayardi — ya'ni «yuza o'smadi» da'vosi
       har safar bittadan o'sib boradigan da'voga aylanardi.

    ⚠ VA U YANGI BOT API METODI HAM EMAS: qiymat AYNAN o'sha bitta
      `sendMessage` chaqiruvining javob tanasidan olinadi.
    =======================================================================
    """
    from app.services.alerts import AlertSender, last_message_id

    assert callable(last_message_id), "`last_message_id` funksiya emas"
    assert not hasattr(AlertSender, "last_message_id"), (
        "`last_message_id` `AlertSender` ga ATRIBUT bo'lib qo'shildi — sinf "
        "yuzasining literal to'plami endi eskirgan va `test_alerting.py` ning "
        "tenglik darvozasi bilan ziddiyatga tushdi"
    )
    assert last_message_id() is None, (
        "modul darajasidagi `ContextVar` ning standarti `None` emas — «hali "
        "chaqiruv bo'lmagan» holati yolg'on identifikator berardi"
    )


def test_forbidden_tokens_are_reachable() -> None:
    """⛔ NAZORAT — predikat ATAYIN EKILGAN matnda haqiqatan ushlaydi.

    Bu darvoza loyihasi bo'yicha HAR DOIM yashil, ya'ni yashil rang uning
    ISHLAYOTGANINI isbotlamaydi. Nazorat bandisiz noto'g'ri yozilgan
    predikat (masalan `token in source` o'rniga `token == source`) mangu
    yashil qolardi va hech nimani o'lchamasdi.
    """
    planted = "\n".join(
        (
            "async def leak(bot, chat_id, path):",
            "    await bot.sendPhoto(chat_id, photo=open(path, 'rb'))",
        )
    )

    caught = sorted(token for token in FORBIDDEN_BOT_API_TOKENS if token in planted)

    assert caught == ["photo=", "sendPhoto"], (
        f"skaner ekilgan satrni topmadi: {caught}. Predikat buzilgan bo'lsa "
        "yuqoridagi darvozalar ham hech nimani o'lchamaydi."
    )
