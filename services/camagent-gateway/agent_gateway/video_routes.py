"""Jonli video marshrutlari (v0.4 server tomoni, SBOZOR-CHECKLIST 2B).

`app.py` bu yerdagi `attach()` ni chaqiradi. Alohida fayl: `app.py`
allaqachon katta, video esa mustaqil qism — sbozor uni butunlay
o'chirib tashlashi ham mumkin.

**Asosiy qaror: cheklovlar UI'da emas, SERVER va AGENTDA majburlanadi.**

Brauzerga ishonib bo'lmaydi: sahifa yiqilishi, tarmoq uzilishi yoki
oyna shunchaki yopilishi mumkin — "men ketdim" signali hech qachon
kelmaydi. Shuning uchun oqim IJARA (lease) asosida ishlaydi: brauzer
har ~15 soniyada "men hali shu yerdaman" deydi. Aytmay qolsa — seans
o'ladi va agentga `stop_stream` ketadi.

**Protokol muzlatilgan** (docs/protocol.md): yangi buyruq qo'shilmaydi.
Ijarani uzaytirish AYNAN `start_stream` ning takroriy chaqiruvi
orqali bo'ladi — agent tomonidagi `StreamManager.start()` mavjud
kalitni ko'rsa muddatni uzaytiradi.
"""
from __future__ import annotations

import asyncio
import html
import json
import logging
import os
import secrets
import time

import requests
from fastapi import Form, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

log = logging.getLogger("agent_gateway.video")

# Brauzer shu oraliqda "tirikman" deyishi kerak. Undan uzoq jim qolsa
# seans yopiladi va agentga stop_stream ketadi.
LEASE_S = 45
# Agentga beriladigan muddat. Ijaradan UZUNROQ: brauzer bitta ping'ni
# o'tkazib yuborsa oqim darrov uzilmasin, lekin unutilgan oqim ham
# ko'pi bilan shuncha yashaydi.
AGENT_DURATION_S = 90
# "Davom etish" tugmasisiz maksimal davomiylik (CLAUDE.md: 10 daqiqa).
MAX_SESSION_S = 600
# ⛔ sbozor SEANSLARI UCHUN IJARA — UZUNROQ (260829). sbozor ijara
#   yubormaydi, u CHIPTANI 5 daqiqada yangilaydi (`LIVE_SESSION_MAX_MS`)
#   va har yangilashda yangi `start` keladi. `LEASE_S` (45 s) qo'llansa
#   video 45 soniyada uzilardi va foydalanuvchi buni «kamera yiqildi»
#   deb tushunardi. Marja chipta yangilanishining kechikishini yopadi.
SBOZOR_LEASE_S = 400
# Har bozorga oylik jonli video byudjeti (daqiqa). Limit tugasa
# obyekt avtomatik "yangilanuvchi rasm" rejimiga tushadi.
#
# ⛔⛔ SOZLANADIGAN QILINDI (260906, Karmanada chegara URILDI).
#
#    600 daqiqa TURN trafigi pul turishini hisobga olib tanlangan edi.
#    Amalda ikki narsa boshqacha chiqdi:
#
#      * TURN hali O'RNATILMAGAN — trafik to'g'ridan-to'g'ri ketadi va
#        hech nima turmaydi, ya'ni chegara HOZIR xarajatni emas, faqat
#        ishni cheklaydi;
#      * kameralar devori 16 katakni BIRDAN ochadi va har biri o'z
#        seansini oladi — bitta sahifa ~2,7 daqiqa yeydi. 600 daqiqa
#        atigi ~200 marta sahifa ochishga yetadi, direktor esa uni
#        kuniga bir necha marta ochadi.
#
#    Chegara O'CHIRILMADI va bu ataylab: TURN qo'yilgan kuni u yagona
#    himoya bo'lib qoladi. Endi u muhitdan o'qiladi, ya'ni obyekt
#    bo'yicha sozlanadi va kod o'zgartirmasdan qaytariladi.
#
# ⚠ `0` YOZILSA CHEKLOV BUTUNLAY O'CHADI — TURN'siz o'rnatmada bu
#   qonuniy tanlov, TURN bilan esa xavfli. Standart ataylab CHEKLOVLI.
MONTHLY_BUDGET_MIN = int(os.environ.get("CAMAGENT_GW_VIDEO_BUDGET_MIN", "600"))


def attach(router, gw, *, check_admin, deny, page, secure, esc, media):
    """Video marshrutlarini routerga ulaydi.

    Bog'liqliklar ATAYIN parametr sifatida beriladi: bu modul `app.py`
    ning ichki holatiga tegmaydi va testda alohida tekshiriladi.
    """

    def _actor(request: Request) -> str:
        """Kim ko'ryapti. Dev panelda IP, sbozor'da haqiqiy foydalanuvchi.

        sbozor `X-Actor` sarlavhasini o'z autentifikatsiyasidan
        to'ldiradi (docs/integration.md). Bu qiymat jurnalga tushadi.
        """
        kim = (request.headers.get("X-Actor") or "").strip()[:80]
        manzil = request.client.host if request.client else "?"
        return kim or f"panel@{manzil}"

    async def _agent_command(agent_id: str, name: str, params: dict,
                             actor: str) -> str:
        cmd_id = gw.db.queue_command(agent_id, name, params)
        gw.db.log_event(agent_id, f"video_{name}",
                        f"kanal {params.get('channel')} ({cmd_id})", actor=actor)
        await gw.push_pending_commands(agent_id)
        return cmd_id

    def _budget_left(agent_id: str) -> float:
        return MONTHLY_BUDGET_MIN - gw.db.stream_minutes_this_month(agent_id)

    async def _stop_if_last(agent_id: str, channel: int, actor: str,
                            besides: str = "", nvr_serial: str = "") -> bool:
        """Oqimni to'xtatadi — FAQAT boshqa ko'ruvchi qolmagan bo'lsa.

        Oqim kalit `{seriya}:{kanal}` bo'yicha yagona: bitta kanalni ikki
        operator ko'rsa, ikkalasi AYNI oqimdan foydalanadi. Shuning uchun
        birovning seansi yopilganda darrov `stop_stream` yuborib bo'lmaydi —
        aks holda ikkinchi operatorning videosi sababsiz o'chadi.

        Jonli sinovda AYNAN shu sodir bo'ldi: eskirgan seans tozalanганda
        o'sha kanaldagi YANGI, faol oqim ham o'chdi.

        ⛔ SOLISHTIRISH KANAL EMAS, `{seriya}:{kanal}` JUFTLIGI BO'YICHA
           (260829). NVR'siz obyektda 16 kameraning HAMMASIDA kanal = 1:
           faqat kanalga qaraganda bitta kamerani yopish qolgan 15 tasini
           «hali ochiq» deb ko'rsatar va HECH BIR oqim to'xtamasdi —
           ular `max_duration_s` gacha ishlab, agentning yuqori oqimini
           va NVR byudjetini bekorga yeb turardi.
        """
        qolgan = [s for s in gw.db.open_stream_sessions(agent_id)
                  if s["channel"] == channel
                  and (s.get("nvr_serial") or "") == (nvr_serial or "")
                  and s["session_id"] != besides]
        if qolgan:
            log.info("kanal %s da yana %d ko'ruvchi bor — oqim to'xtatilmaydi",
                     channel, len(qolgan))
            return False
        await _agent_command(agent_id, "stop_stream",
                             {"channel": channel,
                              "nvr_serial": nvr_serial or ""}, actor)
        return True

    # ------------------------------------------------ eskirgan seanslar

    async def reap_sessions() -> int:
        """Brauzer aloqasi uzilgan seanslarni yopadi va oqimni to'xtatadi.

        BU FUNKSIYA MUHIM: usiz unutilgan sahifa obyektning uplink'ini
        soatlab band qiladi va 4-prinsip buziladi (rasm kechikadi).
        """
        yopilgan = 0
        for seans in gw.db.stale_stream_sessions(LEASE_S, SBOZOR_LEASE_S):
            gw.db.end_stream_session(seans["session_id"], "brauzer javob bermadi")
            await _stop_if_last(seans["agent_id"], seans["channel"], "tizim",
                                nvr_serial=seans.get("nvr_serial") or "")
            log.info("eskirgan video seansi yopildi: %s", seans["session_id"])
            yopilgan += 1
        return yopilgan

    gw.reap_stream_sessions = reap_sessions

    async def reaper_loop() -> None:
        """Eskirgan seanslarni davriy tozalaydi.

        Faqat `stream_start` ichida tozalash YETARLI EMAS: hech kim yangi
        video ochmasa, unutilgan seans yozuvi ochiq qolib, panelda "kimdir
        ko'ryapti" deb turadi.

        Uplink esa BUSIZ HAM himoyalangan: agent serverga ishonmaydi, uning
        o'z taymeri 90 soniyada oqimni o'chiradi. Server
        uzaytirmasa — oqim baribir tugaydi. Bu ikkinchi qatlam.
        """
        while True:
            try:
                await asyncio.sleep(LEASE_S)
                await reap_sessions()
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("video seanslarini tozalashda xato")

    def ensure_background() -> None:
        """Fon vazifalarini birinchi murojaatda ishga tushiradi.

        Nega `startup` hodisasi emas: `include_router()` qo'shilgan
        routerning `lifespan` ini ishga tushirmaydi, `on_event` esa
        eskirgan. sbozor bu routerni o'z app'iga ulaydi — ya'ni ikkala
        yo'l ham ishonchsiz. Kechiktirilgan ishga tushirish esa qayerga
        ulanishidan qat'i nazar ishlaydi.
        """
        if getattr(gw, "_stream_reaper", None) is None:
            try:
                gw._stream_reaper = asyncio.get_running_loop().create_task(
                    reaper_loop())
            except RuntimeError:      # hodisa tsikli yo'q (test/sinxron chaqiruv)
                return

        # ⚠ MEDIA SERVERI HAR MUROJAATDA TEKSHIRILADI, faqat birinchisida
        #   emas: MediaMTX yiqilsa (yoki hech qachon ko'tarilmagan bo'lsa)
        #   jonli video BUTUNLAY o'lardi va uni tiklashning yagona yo'li
        #   gateway'ni qayta ishga tushirish bo'lardi. `start()` o'zi
        #   ishlayotgan jarayonni ko'rsa darrov qaytadi — ya'ni bu
        #   tekshiruv arzon.
        if media.running():
            return
        if media.binary():
            ok, izoh = media.start()
            log.info("media server: %s", izoh)
        else:
            log.info("media server: %s", media.sabab())

    gw.ensure_video_background = ensure_background

    def stop_background() -> None:
        vazifa = getattr(gw, "_stream_reaper", None)
        if vazifa is not None:
            vazifa.cancel()
            gw._stream_reaper = None
        media.stop()

    gw.stop_video_background = stop_background

    # ------------------------------------------------ boshlash

    @router.post("/admin/agent/{agent_id}/stream/start")
    async def stream_start(agent_id: str, request: Request,
                           channel: str = Form(...),
                           nvr_serial: str = Form(default=""),
                           format: str = Form(default="")):
        if not check_admin(request):
            return deny()
        if not channel.isdigit():
            return JSONResponse({"error": "kanal raqam bo'lishi kerak"},
                                status_code=400)
        agent = gw.db.agent_by_id(agent_id)
        if not agent:
            return JSONResponse({"error": "agent topilmadi"}, status_code=404)

        ensure_background()
        await reap_sessions()
        actor = _actor(request)
        kanal = int(channel)

        # Oylik byudjet: tugagan bo'lsa video ochilmaydi, lekin zaxira
        # rejim (yangilanuvchi rasm) ishlaydi — u TURN talab qilmaydi va
        # mavjud HTTPS yo'lidan ketadi.
        qoldi = _budget_left(agent_id)
        rejim = "webrtc" if (media.available() and qoldi > 0) else "rasm"

        session_id = "vs_" + secrets.token_urlsafe(12)
        gw.db.start_stream_session(session_id, agent_id, kanal, actor, rejim,
                                   nvr_serial=nvr_serial or "")
        gw.db.log_event(agent_id, "stream_opened",
                        f"kanal {kanal}, rejim {rejim}", actor=actor)

        if rejim == "webrtc":
            await _agent_command(agent_id, "start_stream", {
                "nvr_serial": nvr_serial or "",
                "channel": kanal,
                "publish_url": media.publish_url(agent_id, kanal,
                                                 nvr_serial or ""),
                "duration_s": AGENT_DURATION_S,
            }, actor)
        if format == "json":
            # To'r sahifasi sahifani almashtirmasdan oqim ochadi.
            return {"session": session_id, "mode": rejim, "channel": kanal}
        return RedirectResponse(
            f"/admin/agent/{agent_id}/stream/{kanal}?s={session_id}",
            status_code=303)

    # ---------------------------------------- sbozor uchun ichki yo'l

    def _internal_ok(request: Request) -> bool:
        """Chaqiruvchi — sbozor core-api'mi.

        ⚠ PANEL TOKENI EMAS, XIZMAT TOKENI. Panel tokeni odamda
          (brauzerda) turadi; bu yo'l esa faqat servisdan chaqiriladi va
          `check_admin` uni qabul qilsa, brauzerdagi har qanday XSS
          bozor kamerasini ocha olardi.

        Token AYNAN `CAMAGENT_SBOZOR_TOKEN` — sbozor'ga kadr xabarini
        yuborishda ishlatiladigan o'sha sir. Ikkala yo'nalish bitta
        ishonch chegarasida (bir compose, ichki tarmoq) va ikkinchi
        sozlama operatorga faqat yana bitta unutiladigan qadam berardi.
        """
        kutilgan = (gw.sbozor.api_token or "").strip()
        if not kutilgan:
            return False
        berilgan = (request.headers.get("authorization") or "").strip()
        if berilgan.lower().startswith("bearer "):
            berilgan = berilgan[7:].strip()
        return secrets.compare_digest(berilgan, kutilgan)

    def _agent_and_serial(market_id: str, camera_serial: str) -> tuple:
        """Bozor UUID'i + kamera seriyasi -> (agent, seriya).

        Seriya agentning `register` da yuborgan ro'yxatidan qidiriladi:
        sbozor'dagi qiymat o'sha ro'yxatdan kelgan, ya'ni mos kelishi
        kerak — kelmasa kamera boshqa agentga ko'chgan yoki o'chirilgan.
        """
        for agent in gw.db.agents_by_prefix(market_id):
            try:
                nvrs = json.loads(agent.get("nvrs_json") or "[]")
            except ValueError:
                continue
            for nvr in nvrs:
                if str(nvr.get("serial") or "") == camera_serial:
                    return agent, camera_serial
        return None, ""

    @router.post("/internal/stream/start")
    async def internal_stream_start(request: Request):
        """sbozor jonli ko'rish uchun oqim so'raydi.

        ⛔⛔ NEGA BU KERAK. sbozor'ning go2rtc'si kameraga TO'G'RIDAN
            -TO'G'RI ulanadi (`rtsp://192.168.1.113`) — bu bozorning
            ICHKI manzili va serverdan unga yo'l YO'Q (1-prinsip:
            modemda port ochilmaydi). Ya'ni «Ko'rish» tugmasi CamAgent
            obyektlarida hech qachon ishlamasdi.

            Bu yerda zanjir teskari yo'nalishda quriladi: agent oqimni
            O'ZI MediaMTX'ga uzatadi, go2rtc esa uni SERVERNING ichida
            o'qiydi. Bozor tarmog'iga hech kim kirmaydi.

        ⚠ IJARA O'ZGARMAYDI: qaytarilgan `session_id` bo'yicha sbozor
          `keepalive` yuborishi SHART, aks holda oqim `LEASE_S` dan
          keyin o'ladi (fayl boshidagi izoh).
        """
        if not _internal_ok(request):
            return JSONResponse({"error": "ruxsat yo'q"}, status_code=403)
        try:
            tana = await request.json()
        except Exception:                              # noqa: BLE001
            return JSONResponse({"error": "json kutilgan"}, status_code=400)

        market_id = str(tana.get("market_id") or "")
        seriya = str(tana.get("camera_serial") or "")
        kanal = tana.get("channel_no")
        if not market_id or not seriya or not str(kanal).isdigit():
            return JSONResponse(
                {"error": "market_id, camera_serial, channel_no kerak"},
                status_code=400)
        kanal = int(kanal)

        agent, seriya = _agent_and_serial(market_id, seriya)
        if not agent:
            return JSONResponse({"error": "kamera hech bir agentda topilmadi"},
                                status_code=404)
        agent_id = agent["agent_id"]

        # ⛔ TARTIB MUHIM: `ensure_background()` MediaMTX'ni KO'TARADI,
        #   `available()` esa uni ISHLAYAPTIMI deb so'raydi. Teskari
        #   tartibda birinchi murojaat HAR DOIM 503 olardi — konteyner
        #   qayta ishga tushgandan keyingi birinchi «Ko'rish» bosilishi
        #   aynan shunday yiqilib, ikkinchisi ishlar va sabab
        #   «vaqti-vaqti bilan ishlamaydi» bo'lib ko'rinardi.
        ensure_background()
        await reap_sessions()

        if not media.available():
            # Zaxira rejim SBOZOR TOMONIDA yo'q: u go2rtc kutadi.
            # 503 -> sbozor «jonli ko'rish hozir ishlamayapti» deydi va
            # «Qayta urinish» beradi (`market-errors.ts`).
            log.warning("media server tayyor emas: %s", media.sabab())
            return JSONResponse({"error": "media server ishlamayapti"},
                                status_code=503)
        if _budget_left(agent_id) <= 0:
            return JSONResponse({"error": "oylik video byudjeti tugadi"},
                                status_code=503)

        actor = str(tana.get("viewer") or "sbozor")
        muddat = int(tana.get("duration_s") or AGENT_DURATION_S)
        # ⛔ PASTKI CHEGARA 10 SONIYA, `AGENT_DURATION_S` EMAS (260829).
        #
        #   `AGENT_DURATION_S` (90 s) — PANEL ijarasining uzunligi va u
        #   brauzer har 15 soniyada «tirikman» deyishiga mo'ljallangan.
        #   sbozor devori esa katakchani 10 soniya jonli ko'rsatib
        #   oxirgi kadrga qaytadi: 90 soniyalik pastki chegara 16 ta
        #   oqimni yana bir yarim daqiqa ushlab turardi — ya'ni tejash
        #   umuman ishlamasdi.
        #
        # ⚠ YUQORI CHEGARA O'ZGARMAYDI: unutilgan oqim `MAX_SESSION_S`
        #   dan uzoq yashamaydi.
        muddat = max(10, min(muddat, int(MAX_SESSION_S)))

        # ⛔ O'SHA KO'RUVCHINING ESKI SEANSI YOPILADI. sbozor dialogi
        #   yopilganda xabar bermaydi; yopilmasa agentdagi
        #   `max_channels` to'lib, uchinchi kamera ochilmasdi.
        for eski in gw.db.open_sessions_of_actor(actor):
            gw.db.end_stream_session(eski["session_id"], "yangi ko'rish")
            await _stop_if_last(eski["agent_id"], eski["channel"], actor,
                                nvr_serial=eski.get("nvr_serial") or "")

        session_id = "vs_" + secrets.token_urlsafe(12)
        # ⚠ QISQA KO'RISH (devor katakchasi) seansi DARHOL YOPIQ
        #   yoziladi — sabab `db.start_stream_session` izohida.
        #   Uzoq ko'rish (dialog) esa ijara bilan ishlaydi.
        qisqa = muddat if muddat <= 60 else 0
        gw.db.start_stream_session(session_id, agent_id, kanal, actor,
                                   "webrtc", nvr_serial=seriya,
                                   duration_s=qisqa)
        gw.db.log_event(agent_id, "stream_opened",
                        f"sbozor, kanal {kanal} ({seriya})", actor=actor)
        await _agent_command(agent_id, "start_stream", {
            "nvr_serial": seriya,
            "channel": kanal,
            "publish_url": media.publish_url(agent_id, kanal, seriya),
            "duration_s": muddat,
        }, actor)

        # ⛔ OQIM KELGUNCHA KUTAMIZ (sabab `media.wait_ready` izohida).
        #   Kutish bloklaydi, shuning uchun oqimga chiqariladi: bitta
        #   sekin agent butun gateway'ni to'xtatib qo'ymasin — kadr
        #   qabul qilish ham shu jarayonda ishlaydi.
        tayyor = await run_in_threadpool(media.wait_ready, agent_id, kanal,
                                         seriya)
        if not tayyor:
            # Seans OCHIQ QOLADI: agent buyruqni oldi va oqim kechroq
            # kelishi mumkin. sbozor 503 ni «Qayta urinish» qiladi va
            # o'shanda yo'l allaqachon tayyor bo'ladi.
            gw.db.log_event(agent_id, "stream_slow",
                            f"kanal {kanal} ({seriya}) belgilangan vaqtda tayyor bo'lmadi",
                            actor=actor)
            # ⛔⛔ AGENT AYTGAN SABAB JAVOBGA QO'SHILADI (261005).
            #
            #     Ilgari bu yerdan faqat "oqim hali tayyor emas" ketardi
            #     va sbozor uni umumiy xatoga aylantirardi — panel esa
            #     bo'shliqni «ehtimol NVR oqim chegarasiga yetgan» deb
            #     TO'LDIRIB qo'yardi. O'sha taxmin Karmanada yolg'on
            #     chiqdi: zanjirda NVR umuman ishtirok etmagan.
            #
            # ⚠ BIRINCHI URINISHDA ODATDA `None` BO'LADI va bu KUTILGAN:
            #   agent sababni heartbeatda (60 s) yuboradi, gateway esa
            #   bir necha soniya kutadi. Ya'ni sabab KEYINGI urinishda
            #   ko'rinadi. Shuning uchun maydon ixtiyoriy — uni majburiy
            #   qilish birinchi urinishni yolg'on sabab bilan
            #   to'ldirishga majburlardi.
            sabab = gw.db.last_stream_failure(agent_id)
            javob = {"error": "oqim hali tayyor emas", "session_id": session_id}
            if sabab:
                javob["agent_reason"] = sabab[:300]
            return JSONResponse(javob, status_code=503)

        return {
            "session_id": session_id,
            "rtsp_url": media.read_url(agent_id, kanal, seriya),
            "lease_s": LEASE_S,
        }

    @router.post("/internal/stream/{session_id}/keepalive")
    async def internal_keepalive(session_id: str, request: Request):
        if not _internal_ok(request):
            return JSONResponse({"error": "ruxsat yo'q"}, status_code=403)
        seans = gw.db.stream_session(session_id)
        if not seans or seans.get("ended_at"):
            return JSONResponse({"ok": False}, status_code=410)
        gw.db.touch_stream_session(session_id)
        await _agent_command(seans["agent_id"], "start_stream", {
            "nvr_serial": seans.get("nvr_serial") or "",
            "channel": seans["channel"],
            "publish_url": media.publish_url(seans["agent_id"],
                                             seans["channel"],
                                             seans.get("nvr_serial") or ""),
            "duration_s": AGENT_DURATION_S,
        }, actor="sbozor")
        return {"ok": True}

    @router.post("/internal/stream/{session_id}/stop")
    async def internal_stop(session_id: str, request: Request):
        if not _internal_ok(request):
            return JSONResponse({"error": "ruxsat yo'q"}, status_code=403)
        seans = gw.db.end_stream_session(session_id, "sbozor yopdi")
        if not seans:
            return JSONResponse({"ok": False}, status_code=404)
        await _stop_if_last(seans["agent_id"], seans["channel"], "sbozor",
                            nvr_serial=seans.get("nvr_serial") or "")
        return {"ok": True}

    # ------------------------------------------------ ijara (keepalive)

    @router.post("/admin/stream/{session_id}/keepalive")
    async def stream_keepalive(session_id: str, request: Request):
        """Brauzer "men hali ochiqman" deydi. Javob — nima qilish kerakligi.

        Shu chaqiruv kelmay qolsa seans o'ladi. Sahifani yopish uchun
        alohida signal SHART EMAS — yo'qlik o'zi signal.
        """
        if not check_admin(request):
            return deny()
        seans = gw.db.stream_session(session_id)
        if not seans or seans.get("ended_at"):
            return JSONResponse({"ok": False, "reason": "seans yopilgan"},
                                status_code=410)

        yosh = time.time() - float(seans["started_at"])
        if yosh > MAX_SESSION_S:
            # 10 daqiqa avto-o'chish. Davom etish uchun operator tugmani
            # bosadi — bu yangi seans ochadi, ya'ni jurnalda ham ko'rinadi.
            gw.db.end_stream_session(session_id, "10 daqiqa muddati tugadi")
            await _stop_if_last(seans["agent_id"], seans["channel"], "tizim",
                                nvr_serial=seans.get("nvr_serial") or "")
            return JSONResponse({"ok": False, "reason": "muddat tugadi",
                                 "renewable": True}, status_code=410)

        gw.db.touch_stream_session(session_id)
        if seans.get("mode") == "webrtc":
            # Agentdagi ijarani ham uzaytiramiz. Yangi buyruq emas —
            # AYNI `start_stream` (protokol muzlatilgan). `nvr_serial`
            # seansdan olinadi: ikki NVR'li obyektda serialsiz buyruq
            # birinchi NVR'ga tushib, boshqa kamerani ochib yuborardi.
            await _agent_command(seans["agent_id"], "start_stream", {
                "nvr_serial": seans.get("nvr_serial") or "",
                "channel": seans["channel"],
                "publish_url": media.publish_url(seans["agent_id"],
                                                 seans["channel"],
                                                 seans.get("nvr_serial") or ""),
                "duration_s": AGENT_DURATION_S,
            }, actor="tizim")
        return {"ok": True, "qolgan_s": int(MAX_SESSION_S - yosh),
                "rejim": seans.get("mode")}

    # ------------------------------------------------ to'xtatish

    @router.post("/admin/stream/{session_id}/stop")
    async def stream_stop(session_id: str, request: Request):
        if not check_admin(request):
            return deny()
        seans = gw.db.end_stream_session(session_id, "operator yopdi")
        if not seans:
            return JSONResponse({"ok": False}, status_code=404)
        await _stop_if_last(seans["agent_id"], seans["channel"], _actor(request),
                            nvr_serial=seans.get("nvr_serial") or "")
        gw.db.log_event(seans["agent_id"], "stream_closed",
                        f"kanal {seans['channel']}", actor=_actor(request))
        return {"ok": True}

    # ------------------------------------------------ WHEP proksi

    @router.post("/admin/stream/{session_id}/whep")
    async def whep_proxy(session_id: str, request: Request):
        """WebRTC signalizatsiyasi — mavjud HTTPS porti orqali.

        MediaMTX faqat localhost'da tinglaydi. Brauzer unga to'g'ridan
        -to'g'ri kira olmaydi, chunki u holda havolani bilgan HAR KIM
        kamerani ko'rardi — bu yerdagi huquq tekshiruvi chetlab o'tilardi.
        Yangi ommaviy port ham ochilmaydi.
        """
        if not check_admin(request):
            return deny()
        seans = gw.db.stream_session(session_id)
        if not seans or seans.get("ended_at"):
            return JSONResponse({"error": "seans yopilgan"}, status_code=410)
        if not media.available():
            return JSONResponse({"error": media.sabab()}, status_code=503)

        sdp = await request.body()
        url = media.whep_url(seans["agent_id"], seans["channel"],
                             seans.get("nvr_serial") or "")
        try:
            # `requests` BLOKLOVCHI. To'g'ridan-to'g'ri `async` ichida
            # chaqirilsa butun hodisa tsikli to'xtaydi va 12 obyektning
            # heartbeat'i bitta video ulanishi ortida navbatga tushadi.
            javob = await run_in_threadpool(
                lambda: requests.post(url, data=sdp, timeout=10,
                                      headers={"Content-Type": "application/sdp"}))
        except requests.RequestException as exc:
            log.warning("WHEP proksi xatosi: %s", exc)
            return JSONResponse({"error": "media server javob bermadi"},
                                status_code=502)
        gw.db.touch_stream_session(session_id)
        return Response(javob.content, status_code=javob.status_code,
                        media_type=javob.headers.get("Content-Type",
                                                     "application/sdp"))

    # ------------------------------------------------ zaxira rejim

    @router.get("/admin/stream/{session_id}/frame")
    async def stream_frame(session_id: str, request: Request):
        """Zaxira rejim: eng oxirgi kadr.

        WebRTC ulanmasa yoki byudjet tugasa shu ishlaydi. TURN kerak
        emas, mavjud HTTPS yo'lidan ketadi va sekin internetda ham
        ochiladi. Video emas, lekin "hozir nima bo'lyapti" degan savolga
        javob beradi — 4-prinsipga mos: video — qulaylik.
        """
        if not check_admin(request):
            return deny()
        seans = gw.db.stream_session(session_id)
        if not seans or seans.get("ended_at"):
            return JSONResponse({"error": "seans yopilgan"}, status_code=410)
        gw.db.touch_stream_session(session_id)

        snap = gw.db.latest_snapshot(seans["agent_id"], seans["channel"])
        if not snap:
            return JSONResponse({"error": "bu kanaldan hali rasm yo'q"},
                                status_code=404)
        try:
            # S3 rejimida bu tarmoq chaqirig'i — threadpool'da; xato sinfi
            # ham backend'ga qarab farq qiladi (boto3 ClientError va h.k.).
            kadr = await run_in_threadpool(gw.storage.open_snapshot,
                                           snap["storage_ref"])
        except Exception:                                     # noqa: BLE001
            return JSONResponse({"error": "rasm o'qilmadi"}, status_code=404)
        return secure(Response(kadr, media_type="image/jpeg",
                               headers={"Cache-Control": "no-store"}))

    @router.get("/admin/agent/{agent_id}/frame/{channel}")
    async def agent_frame(agent_id: str, channel: int, request: Request):
        """Kanalning oxirgi kadri — oqim seansi TALAB QILINMAYDI.

        To'r ko'rinishida 13 ta kamera bir vaqtda ko'rinadi. Ularning
        har biri uchun oqim ochish mumkin emas: `max_channels` 2 ta va
        13 ta jonli oqim bozorning uplink'ini butunlay band qiladi
        (13 x ~500 kbit/s). Shuning uchun to'r RASMLARDAN quriladi —
        ular allaqachon serverda va qo'shimcha trafik talab qilmaydi.
        """
        if not check_admin(request):
            return deny()
        snap = gw.db.latest_snapshot(agent_id, channel)
        if not snap:
            return JSONResponse({"error": "bu kanaldan hali rasm yo'q"},
                                status_code=404)
        try:
            kadr = await run_in_threadpool(gw.storage.open_snapshot,
                                           snap["storage_ref"])
        except Exception:                                     # noqa: BLE001
            return JSONResponse({"error": "rasm o'qilmadi"}, status_code=404)
        return secure(Response(kadr, media_type="image/jpeg", headers={
            "Cache-Control": "no-store",
            # Kadr QACHON olingani — to'rda ko'rsatiladi. Uch soatlik
            # kadrni jonli deb ko'rsatish eng qimmat yolg'on bo'lardi.
            "X-Received-At": str(int(snap["received_at"])),
            "X-Late": "1" if snap["late"] else "0"}))

    # ------------------------------------------------ to'r ko'rinishi

    @router.get("/admin/agent/{agent_id}/wall", response_class=HTMLResponse)
    async def camera_wall(agent_id: str, request: Request):
        """Barcha kameralar bir ekranda (Hik-Connect uslubida).

        **Nega hammasi jonli video EMAS.** Agentda `max_channels` chegarasi
        bor (standart 2) va bu tasodifiy emas: 13 ta jonli oqim bozorning
        uplink'idan ~6.5 Mbit/s doimiy talab qiladi va rasm yuborishni
        kechiktiradi — ya'ni 4-prinsip buziladi ("rasm — bu pul").

        Shuning uchun to'r RASMLARDAN quriladi (ular allaqachon serverda,
        qo'shimcha trafik yo'q), kerakli kamerani bosganda esa o'sha bitta
        kanal jonli videoga aylanadi.
        """
        if not check_admin(request):
            return deny()
        agent = gw.db.agent_by_id(agent_id)
        if not agent:
            return secure(HTMLResponse(page("Topilmadi",
                                            "<h1>Obyekt topilmadi</h1>"),
                                       status_code=404))
        nvrs = json.loads(agent.get("nvrs_json") or "[]")
        cfg = gw.config_for(agent) or {}
        limit = int((cfg.get("stream") or {}).get("max_channels", 2))

        # ⛔⛔ KALIT — `seriya|kanal`, FAQAT KANAL EMAS (260829, Karmanada
        #     o'lchandi).
        #
        #     NVR'siz obyektda har kamera ALOHIDA qurilma va hammasining
        #     kanali `1`. Kalit sifatida faqat kanal raqami olinganda
        #     brauzer 16 ta kamerani BITTA deb hisoblardi: birinchisi
        #     ochilgach qolganlari «allaqachon jonli» bo'lib `return`
        #     qilardi va «Barchasini yoqish» hech narsa qilmasdi.
        kataklar, kalitlar = [], []
        for nvr in nvrs:
            seriya = str(nvr.get("serial") or "")
            for c in nvr.get("channels") or []:
                if not c.get("enabled", True):
                    continue
                ch = int(c.get("id", 0))
                kalit = f"{seriya}|{ch}"
                kalitlar.append(kalit)
                kataklar.append(
                    f"<div class='cam' data-key='{esc(kalit)}' "
                    f"data-ch='{ch}' data-serial='{esc(seriya)}'>"
                    f"<div class='camview'>"
                    f"<video muted playsinline autoplay></video>"
                    f"<button class='play' title='jonli ko`rish'>&#9654;</button>"
                    f"<span class='badge'></span></div>"
                    f"<div class='camcap'><b>{ch}</b> "
                    f"{esc(c.get('name'))}</div></div>")

        body = f"""<h1>{esc(agent.get('market_name'))} — barcha kameralar</h1>
<p class="hint"><a href="/admin/agent/{esc(agent_id)}">&larr; obyekt sahifasi</a>
&middot; {len(kalitlar)} ta kamera &middot; jonli video bir vaqtda
<b>{limit}</b> tagacha</p>
<div class="panel">
  <button id="barchasi">Barchasini yoqish</button>
  <button id="ochirish">Barchasini o'chirish</button>
  <span class="hint" id="holat"></span>
</div>
<p class="hint">Kameradagi <b>&#9654;</b> tugmasini bosing — jonli video
ochiladi. <b>Ikki marta bosilsa</b> katta ko'rinishga o'tadi
(chiqish — yana ikki marta bosing yoki Esc).</p>
<div class="wall">{''.join(kataklar) or "<p class='empty'>kanal yo`q</p>"}</div>
<script src="/admin/stream/wall.js" defer></script>
<script id="cfg" type="application/json">{json.dumps(
    {"agent": agent_id, "channels": kalitlar, "limit": limit})}</script>"""

        javob = HTMLResponse(page(f"{agent.get('market_name')} — kameralar", body))
        javob.headers["Content-Security-Policy"] = (
            "default-src 'none'; img-src 'self' blob:; media-src 'self' blob:; "
            "script-src 'self'; style-src 'unsafe-inline'; connect-src 'self'; "
            "form-action 'self'; base-uri 'none'; frame-ancestors 'none'")
        javob.headers["X-Content-Type-Options"] = "nosniff"
        javob.headers["X-Frame-Options"] = "DENY"
        javob.headers["Referrer-Policy"] = "no-referrer"
        return javob

    @router.get("/admin/stream/wall.js")
    async def wall_js(request: Request):
        if not check_admin(request):
            return deny()
        return Response(_WALL_JS, media_type="application/javascript",
                        headers={"X-Content-Type-Options": "nosniff",
                                 "Cache-Control": "no-store"})

    # ------------------------------------------------ pleyer sahifasi

    @router.get("/admin/agent/{agent_id}/stream/{channel}",
                response_class=HTMLResponse)
    async def stream_page(agent_id: str, channel: int, request: Request,
                          s: str = ""):
        if not check_admin(request):
            return deny()
        seans = gw.db.stream_session(s) if s else None
        if not seans or seans.get("ended_at"):
            return secure(HTMLResponse(page(
                "Seans yopilgan",
                f"<h1>Seans yopilgan</h1><p class='hint'>"
                f"<a href='/admin/agent/{esc(agent_id)}'>&larr; obyektga qaytish</a>"
                f"</p>"), status_code=410))

        agent = gw.db.agent_by_id(agent_id) or {}
        rejim = seans.get("mode") or "rasm"
        qoldi = _budget_left(agent_id)
        sabab = media.sabab()

        izoh = ""
        if rejim != "webrtc":
            nega = (f"Oylik jonli video limiti tugagan ({MONTHLY_BUDGET_MIN} daqiqa)."
                    if qoldi <= 0 else html.escape(sabab))
            izoh = (f"<div class='panel alert'><b>Yangilanuvchi rasm rejimi.</b> "
                    f"{nega} Rasm har 3 soniyada yangilanadi.</div>")

        body = f"""<h1>Jonli ko'rish — kanal {channel}</h1>
<p class="hint">{esc(agent.get('market_name'))} &middot;
<a href="/admin/agent/{esc(agent_id)}">&larr; obyektga qaytish</a></p>
{izoh}
<div class="panel">
  <div id="sahna" style="background:#000;border-radius:6px;overflow:hidden">
    <video id="v" autoplay muted playsinline
           style="width:100%;display:{'block' if rejim == 'webrtc' else 'none'}"></video>
    <img id="kadr" alt="oxirgi kadr"
         style="width:100%;display:{'none' if rejim == 'webrtc' else 'block'}">
  </div>
  <p id="holat" class="hint">Ulanmoqda…</p>
  <form id="qayta" method="post" action="/admin/agent/{esc(agent_id)}/stream/start"
        style="display:none">
    <input type="hidden" name="channel" value="{channel}">
    <input type="hidden" name="nvr_serial" value="{esc(seans.get('nvr_serial') or '')}">
    <button>Davom etish</button>
  </form>
  <button id="yopish">Yopish</button>
</div>
<p class="hint">Oqim <b>sub-oqim</b>dan olinadi va faqat shu sahifa ochiq
turganda ishlaydi. Jadval vaqti kelsa oqim avtomatik to'xtaydi —
<b>rasm birinchi</b>. Oyiga qolgan: {int(max(0, qoldi))} daqiqa.</p>
<script src="/admin/stream/player.js" defer></script>
<script id="cfg" type="application/json">{json.dumps({
    "session": s, "mode": rejim, "agent": agent_id, "channel": channel})}</script>"""
        javob = HTMLResponse(page(f"Kanal {channel}", body))
        # Pleyer uchun CSP yumshatiladi — LEKIN faqat shu sahifada va
        # faqat o'z domenimizdagi skriptga. `unsafe-inline` berilmaydi:
        # sahifadagi maydonlar baribir qochiriladi, skript esa alohida
        # faylda turadi va o'zgarmaydi.
        javob.headers["Content-Security-Policy"] = (
            "default-src 'none'; img-src 'self' blob:; media-src 'self' blob:; "
            "script-src 'self'; style-src 'unsafe-inline'; connect-src 'self'; "
            "form-action 'self'; base-uri 'none'; frame-ancestors 'none'")
        javob.headers["X-Content-Type-Options"] = "nosniff"
        javob.headers["X-Frame-Options"] = "DENY"
        javob.headers["Referrer-Policy"] = "no-referrer"
        return javob

    @router.get("/admin/stream/player.js")
    async def player_js(request: Request):
        if not check_admin(request):
            return deny()
        return Response(_PLAYER_JS, media_type="application/javascript",
                        headers={"X-Content-Type-Options": "nosniff",
                                 "Cache-Control": "no-store"})


# Pleyer alohida faylda: CSP `script-src 'self'` bo'lishi uchun sahifa
# ichida inline skript bo'lmasligi kerak (XSS himoyasi saqlanadi).
_PLAYER_JS = r"""
(function () {
  var cfg = JSON.parse(document.getElementById('cfg').textContent);
  var holat = document.getElementById('holat');
  var video = document.getElementById('v');
  var kadr = document.getElementById('kadr');
  var qayta = document.getElementById('qayta');
  var yopish = document.getElementById('yopish');
  var tirik = true, jonli = false, pc = null;

  // Oqim TAYYOR BO'LMASLIGI MUMKIN. Agentning ffmpeg'i NVR'ga ulanib
  // uzatishni boshlaguncha bir necha soniya ketadi va media server
  // bu vaqtda 404 qaytaradi. Bir marta so'rab taslim bo'lsak, operator
  // videoni HECH QACHON ko'rmaydi (jonli sinovda aynan shu bo'ldi).
  var URINISH = 0, MAX_URINISH = 12, ORALIQ = 2500;

  function yoz(matn) { holat.textContent = matn; }

  function rasmniYoq() {
    kadr.style.display = 'none';
    video.style.display = 'block';
  }

  // Rasm rejimi DARHOL boshlanadi: operator kutib o'tirmasin, oxirgi
  // kadrni ko'rsin. Video tayyor bo'lganda ustiga o'tamiz.
  function rasmTsikli() {
    if (!tirik || jonli) return;
    kadr.src = '/admin/stream/' + cfg.session + '/frame?t=' + Date.now();
    setTimeout(rasmTsikli, 3000);
  }

  function taslim(sabab) {
    if (pc) { try { pc.close(); } catch (e) {} pc = null; }
    video.style.display = 'none';
    kadr.style.display = 'block';
    yoz(sabab + ' — yangilanuvchi rasm rejimi (har 3 soniyada yangi kadr).');
  }

  async function webrtc() {
    if (!tirik || jonli) return;
    URINISH++;
    try {
      if (pc) { try { pc.close(); } catch (e) {} }
      pc = new RTCPeerConnection({ iceServers: [] });
      pc.addTransceiver('video', { direction: 'recvonly' });
      pc.ontrack = function (e) {
        jonli = true;
        video.srcObject = e.streams[0];
        rasmniYoq();
        yoz('Jonli.');
      };
      pc.onconnectionstatechange = function () {
        if (tirik && pc && pc.connectionState === 'failed') {
          jonli = false;
          taslim('Video ulanmadi');
          rasmTsikli();
        }
      };
      var offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      var r = await fetch('/admin/stream/' + cfg.session + '/whep', {
        method: 'POST',
        headers: { 'Content-Type': 'application/sdp' },
        body: offer.sdp
      });
      if (r.status === 410) { tirik = false; yoz('Seans yopildi.'); return; }
      if (!r.ok) {
        // 404 = oqim hali kelmagan. Kutamiz va qayta urinamiz.
        if (URINISH < MAX_URINISH) {
          yoz('Oqim tayyorlanmoqda… (' + URINISH + '/' + MAX_URINISH + ')');
          setTimeout(webrtc, ORALIQ);
        } else {
          taslim('Video ochilmadi');
        }
        return;
      }
      var answer = await r.text();
      await pc.setRemoteDescription({ type: 'answer', sdp: answer });
    } catch (e) {
      if (URINISH < MAX_URINISH) { setTimeout(webrtc, ORALIQ); }
      else { taslim('Video ochilmadi'); }
    }
  }

  async function ijara() {
    if (!tirik) return;
    try {
      var r = await fetch('/admin/stream/' + cfg.session + '/keepalive',
                          { method: 'POST' });
      if (r.status === 410) {
        var j = await r.json().catch(function () { return {}; });
        tirik = false;
        if (pc) { try { pc.close(); } catch (e) {} }
        video.srcObject = null;
        yoz(j.reason === 'muddat tugadi'
            ? '10 daqiqa tugadi. Davom etish uchun tugmani bosing.'
            : 'Seans yopildi.');
        if (qayta) qayta.style.display = 'block';
        return;
      }
    } catch (e) { /* tarmoq uzildi — keyingi urinishda tiklanadi */ }
    setTimeout(ijara, 15000);
  }

  // Sahifa yopilganda darhol xabar beramiz. Bu YETARLI EMAS (brauzer
  // yiqilsa signal kelmaydi) — shuning uchun serverda ijara muddati
  // bor. Bu shunchaki tezroq bo'shatish.
  window.addEventListener('pagehide', function () {
    tirik = false;
    navigator.sendBeacon('/admin/stream/' + cfg.session + '/stop');
  });

  yopish.addEventListener('click', function () {
    tirik = false;
    fetch('/admin/stream/' + cfg.session + '/stop', { method: 'POST' })
      .finally(function () { history.back(); });
  });

  // "Davom etish" — oddiy forma POST'i. Yangi seans ochiladi, ya'ni
  // jurnalda yangi yozuv qoladi: "kim qancha ko'rdi" hisobi uzilmaydi.

  rasmTsikli();                       // darhol nimadir ko'rinsin
  if (cfg.mode === 'webrtc') { yoz('Oqim tayyorlanmoqda…'); webrtc(); }
  else { taslim('Video mavjud emas'); }
  setTimeout(ijara, 15000);
})();
"""


# To'r ko'rinishi. Alohida fayl: CSP `script-src 'self'` bo'lishi uchun
# sahifada inline skript bo'lmasligi kerak (XSS himoyasi saqlanadi).
_WALL_JS = r"""
(function () {
  var cfg = JSON.parse(document.getElementById('cfg').textContent);
  var holat = document.getElementById('holat');
  // ⛔ KALIT `seriya|kanal` (260829): NVR'siz obyektda 16 kameraning
  //    hammasida kanal `1` va faqat kanal bo'yicha ular BITTA kamera
  //    bo'lib ko'rinardi — birinchisi ochilgach qolganlari «allaqachon
  //    jonli» deb rad etilardi.
  var jonlilar = {};                    // kalit -> {pc, session}

  function katak(k) {
    return document.querySelector('.cam[data-key="' + k + '"]');
  }
  function belgi(ch, matn, sinf) {
    var b = katak(ch).querySelector('.badge');
    b.textContent = matn || '';
    b.className = 'badge' + (sinf ? ' ' + sinf : '');
  }

  async function ochir(ch) {
    var el = katak(ch), v = el.querySelector('video');
    var s = jonlilar[ch];
    delete jonlilar[ch];
    if (s) {
      if (s.pc) { try { s.pc.close(); } catch (e) {} }
      try {
        await fetch('/admin/stream/' + s.session + '/stop', { method: 'POST' });
      } catch (e) {}
    }
    v.srcObject = null;
    el.classList.remove('bor');
    belgi(ch, '');
  }

  async function och(ch) {
    if (jonlilar[ch]) return;
    if (Object.keys(jonlilar).length >= cfg.limit) {
      holat.textContent = 'Bir vaqtda ' + cfg.limit + ' tagacha mumkin.';
      setTimeout(function () { holat.textContent = ''; }, 5000);
      return;
    }
    jonlilar[ch] = { session: null, pc: null };
    belgi(ch, 'ulanmoqda', 'kutish');
    var el = katak(ch);
    var fd = new FormData();
    fd.append('channel', el ? el.getAttribute('data-ch') : ch);
    fd.append('nvr_serial', el ? el.getAttribute('data-serial') : '');
    fd.append('format', 'json');
    try {
      var r = await fetch('/admin/agent/' + cfg.agent + '/stream/start',
                          { method: 'POST', body: fd });
      if (!r.ok) { belgi(ch, 'xato', 'xato'); delete jonlilar[ch]; return; }
      var j = await r.json();
      if (!jonlilar[ch]) return;              // shu orada o'chirilgan
      jonlilar[ch].session = j.session;
      if (j.mode !== 'webrtc') { belgi(ch, 'video yo`q', 'xato'); return; }
      ulan(ch, j.session, 0);
    } catch (e) { belgi(ch, 'xato', 'xato'); delete jonlilar[ch]; }
  }

  // Oqim darrov tayyor bo'lmaydi: agent ffmpeg'i NVR'ga ulanib uzatishni
  // boshlaguncha media server 404 qaytaradi. Bir marta so'rab taslim
  // bo'lsak, operator videoni hech qachon ko'rmaydi.
  async function ulan(ch, session, urinish) {
    if (!jonlilar[ch]) return;
    var el = katak(ch), v = el.querySelector('video');
    try {
      var pc = new RTCPeerConnection({ iceServers: [] });
      jonlilar[ch].pc = pc;
      pc.addTransceiver('video', { direction: 'recvonly' });
      pc.ontrack = function (e) {
        v.srcObject = e.streams[0];
        el.classList.add('bor');
        belgi(ch, 'JONLI', 'jonli');
      };
      var offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      var r = await fetch('/admin/stream/' + session + '/whep', {
        method: 'POST', headers: { 'Content-Type': 'application/sdp' },
        body: offer.sdp });
      if (!r.ok) {
        try { pc.close(); } catch (e) {}
        if (urinish < 20 && jonlilar[ch]) {
          belgi(ch, 'ulanmoqda ' + (urinish + 1), 'kutish');
          setTimeout(function () { ulan(ch, session, urinish + 1); }, 2000);
        } else { belgi(ch, 'ochilmadi', 'xato'); ochir(ch); }
        return;
      }
      await pc.setRemoteDescription({ type: 'answer', sdp: await r.text() });
    } catch (e) {
      if (urinish < 20 && jonlilar[ch]) {
        setTimeout(function () { ulan(ch, session, urinish + 1); }, 2000);
      } else { belgi(ch, 'ochilmadi', 'xato'); ochir(ch); }
    }
  }

  // ---- katta ko'rinish (ikki marta bosish) ----
  function katta(el) {
    document.querySelectorAll('.cam.katta').forEach(function (x) {
      if (x !== el) x.classList.remove('katta');
    });
    el.classList.toggle('katta');
    document.body.classList.toggle('kattada', !!document.querySelector('.cam.katta'));
  }
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      document.querySelectorAll('.cam.katta').forEach(function (x) {
        x.classList.remove('katta');
      });
      document.body.classList.remove('kattada');
    }
  });

  document.querySelectorAll('.cam').forEach(function (el) {
    var ch = el.getAttribute('data-key');
    el.querySelector('.play').addEventListener('click', function (e) {
      e.stopPropagation();
      if (jonlilar[ch]) { ochir(ch); } else { och(ch); }
    });
    el.addEventListener('dblclick', function () { katta(el); });
  });

  document.getElementById('barchasi').addEventListener('click', function () {
    cfg.channels.forEach(function (ch, i) {
      setTimeout(function () { och(ch); }, i * 400);   // NVR'ni bo'g'masin
    });
  });
  document.getElementById('ochirish').addEventListener('click', function () {
    Object.keys(jonlilar).forEach(ochir);
  });

  // Ijara: sahifa ochiq turganda oqimlar tirik qoladi.
  async function ijara() {
    for (var ch in jonlilar) {
      var s = jonlilar[ch];
      if (!s.session) continue;
      try {
        var r = await fetch('/admin/stream/' + s.session + '/keepalive',
                            { method: 'POST' });
        if (r.status === 410) { ochir(ch); }
      } catch (e) {}
    }
    setTimeout(ijara, 15000);
  }

  window.addEventListener('pagehide', function () {
    for (var ch in jonlilar) {
      if (jonlilar[ch].session) {
        navigator.sendBeacon('/admin/stream/' + jonlilar[ch].session + '/stop');
      }
    }
  });

  setTimeout(ijara, 15000);
})();
"""
