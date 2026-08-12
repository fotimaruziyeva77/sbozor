"""`bot-service` ning YAGONA kirish nuqtasi — aiogram long-polling (DQ-1).

=============================================================================
⛔ HANDLERLAR BU FAYLDA (VA BU REJADA) YO'Q — VA BU ATAYIN.

`dp` bo'sh router bilan ishga tushadi: bot bugun `/start` ga ham JAVOB
BERMAYDI. Handlerlar 07-11 niki. Skelet ulardan OLDIN yoziladi, chunki
uchinchi servisning tug'ilishi `compose.yaml`, `package.json` va
`test_sentry_processes.py` darvozasiga TEGADI — bu uch o'zgarish
handlerlar bilan bir commitda aralashsa, darvozaning qizarishi «handler
buzuq» deb o'qilardi. Holat `README.md` §5 da ochiq yozilgan.

=============================================================================
⚠⚠ WEBHOOK QURILMAYDI — LONG-POLLING (DQ-1).

`setWebhook` HTTPS talab qiladi, bu repoda esa TLS YO'Q
(`ops/nginx/nginx.conf`: `listen 80`, sertifikat 8-faza ishi). Bundan
tashqari `getUpdates` va webhook O'ZARO ISTISNO — «ikkalasi ham bo'lsin»
degan variant Bot API da MAVJUD EMAS.

⛔ BIR TOKENGA AYNAN BITTA POLLER. Ikkinchi jarayon `409 Conflict` oladi
   yoki update'ni TORTIB OLADI. Shuning uchun `compose.yaml` da
   `deploy.replicas` YOZILMAYDI va `TelegramConflictError` quyida JIM
   YUTILMAYDI (Pitfall 5).
=============================================================================
"""

from __future__ import annotations

import asyncio

import sentry_sdk
import structlog
from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramConflictError
from aiogram.fsm.storage.redis import RedisStorage

from app.observability import init_sentry
from app.settings import Settings, get_settings

log = structlog.get_logger(__name__)

settings: Settings = get_settings()

bot = Bot(token=settings.telegram_bot_token.get_secret_value())
"""Telegram mijozi — MODUL DARAJASIDA.

⚠ Konstruktor tarmoqqa CHIQMAYDI: u faqat token SHAKLINI tekshiradi
  (`<raqamlar>:<sir>`). Ya'ni bu satr `bot-tests` konteynerida ham
  bemalol import qilinadi va `test_sentry_entrypoints.py` obyekt
  darajasida o'lchay oladi.
"""

storage = RedisStorage.from_url(settings.valkey_url)
"""FSM ombori — Valkey `db 1` (sabab: `app/settings.py::DEFAULT_VALKEY_URL`).

⚠ `from_url` ham tarmoqqa CHIQMAYDI: `redis.asyncio` ulanish pulini
  DANGASA quradi va birinchi buyruqqacha soket ochilmaydi.
"""

dp = Dispatcher(storage=storage)
"""Update yo'naltiruvchi. ⛔ ROUTERLAR HOZIRCHA ULANMAGAN (07-11)."""


async def _on_startup() -> None:
    """Ishga tushish ilmog'i — `dp.startup` REYESTRIGA ro'yxatga olinadi.

    =========================================================================
    ⚠⚠ NEGA ILMOQ, NEGA MODUL DARAJASIDAGI CHAQIRUV EMAS.

    `init_sentry()` ni modul darajasida chaqirish IMPORT ning yon
    ta'siriga aylanardi: `bot-tests` konteynerida `app.main` ni import
    qilgan HAR test Sentry'ni haqiqiy DSN bilan o'rnatib yuborardi va CI
    xatolari mijozning Sentry loyihasiga oqib tushardi. Aynan shu sababdan
    `compose.yaml` da `bot-tests` ga `SENTRY_DSN` BERILMAYDI, ilmoq esa
    faqat `start_polling` da ateshlanadi.

    Ikkala darvoza ham AYNAN SHU ILMOQNI o'lchaydi:
      `tests/unit/test_sentry_processes.py` — `FOREIGN_HOOK_MARKERS` da
          `"dp.startup.register"` markeri (MANBA darajasi)
      `services/bot-service/tests/unit/test_sentry_entrypoints.py` —
          `dp.startup` observeriga ro'yxatga olingan callback'lar
          MANBASIDA `init_sentry(` (REYESTR darajasi)
    =========================================================================
    """
    log.info("sentry", enabled=init_sentry(settings.sentry_dsn))

    # =====================================================================
    # ⛔ WEBHOOK O'CHIRILADI — HAR ISHGA TUSHISHDA, SHARTSIZ.
    #
    # Token WEBHOOK HOLATINI TASHIYDI: u ilgari (sinov paytida yoki boshqa
    # muhitda) `setWebhook` bilan ishlatilgan bo'lsa, `getUpdates` `409`
    # beradi va bot HECH QANDAY update olmaydi. Nosozlik shakli eng yomon
    # sinfdan: konteyner `Up`, jurnal toza, sotuvchilar javob olmaydi.
    #
    # ⚠ `drop_pending_updates=False` — VA BU MUHIM: `True` bo'lsa
    #   qayta ishga tushish paytida kelgan sotuvchi xabarlari JIMGINA
    #   yo'qolardi. Botning butun qiymati «sotuvchi yozgan xabar javob
    #   oladi» degani, ya'ni yo'qotish narxi qayta ishlash narxidan
    #   yuqori.
    # =====================================================================
    await bot.delete_webhook(drop_pending_updates=False)


dp.startup.register(_on_startup)


async def _main() -> None:
    """Long-polling siklini yuritadi va `409` ni JIM YUTMAYDI (Pitfall 5)."""
    try:
        await dp.start_polling(bot)
    except TelegramConflictError as error:
        # =================================================================
        # ⛔ BU ISTISNO YUTILMAYDI VA U `warning` DARAJASIGA TUSHIRILMAYDI.
        #
        # `409 Conflict` AYNAN BITTA narsani anglatadi: SHU TOKEN bilan
        # boshqa joyda ikkinchi `getUpdates` oqimi ishlayapti. Amaliy
        # holat — dasturchining dev mashinasi prod tokenini olgan; o'shanda
        # PROD bot jim bo'lib qoladi va hech qanday xato CHIQMAYDI.
        #
        # `restart: unless-stopped` ostida jim yutilgan istisno cheksiz
        # qayta urinish siklini tug'dirardi va jurnalda faqat takrorlanuvchi
        # shovqin qolardi. Shuning uchun: CRITICAL + Sentry + QAYTA
        # KO'TARILADI — konteyner yiqiladi va sabab ko'rinadi.
        #
        # ⚠ `sentry_sdk.capture_exception` — `app/observability.py` dagi
        #   «SDK faqat o'sha modulda sozlanadi» qoidasini BUZMAYDI: taqiq
        #   SOZLASH chaqiruviga tegishli, XABAR BERISH chaqiruviga emas
        #   (o'sha faylning docstringi). Bu faylda sozlash chaqiruvi YO'Q
        #   va uning literal sanog'i 07-01 ning qabul mezoni.
        # =================================================================
        log.critical(
            "telegram_conflict",
            reason=(
                "shu token bilan IKKINCHI getUpdates oqimi ishlayapti — "
                "bitta tokenga aynan bitta poller (DQ-1). Lokal ishlab "
                "chiqishda ALOHIDA dev bot tokeni ishlatilsin."
            ),
        )
        sentry_sdk.capture_exception(error)
        raise


main = _main
"""⛔ MODUL DARAJASIDAGI ATRIBUT — VA U QULAYLIK UCHUN EMAS.

=============================================================================
`compose.yaml` bu konteynerni `["python", "-m", "app.main"]` bilan
yuritadi, ya'ni `command` da `modul:atribut` shaklidagi token YO'Q.
`tests/unit/test_sentry_processes.py` ning (b) bosqichi shu holatda
`-m <modul>` juftligini o'qiydi va atribut sifatida `MODULE_RUN_ATTRIBUTE`
(= `"main"`) ni oladi; (c) bosqichi esa manbada
`^main\\s*[:=]` shaklidagi MODUL DARAJASIDAGI e'lonni TALAB qiladi.

⚠ `async def main()` BU SHARTNI BAJARMAYDI: u `^main\\s*[:=]` emas,
  `^async def main` bo'lib yoziladi. Shuning uchun funksiya `_main` deb
  ta'riflanadi va shu yerda NOM sifatida bog'lanadi — darvoza matnni
  ko'radi, `python -m` esa quyidagi `__main__` blokidan yuradi.

⛔ Bu ikki qatorni «ortiqcha» deb olib tashlash darvozani QIZARTIRADI va
   bu ATAYIN: kirish nuqtasining nomi jimgina o'zgarib ketmasin.
=============================================================================
"""


if __name__ == "__main__":
    asyncio.run(main())
