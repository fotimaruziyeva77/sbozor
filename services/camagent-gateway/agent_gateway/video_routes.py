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
# Har bozorga oylik jonli video byudjeti (daqiqa). Limit tugasa
# obyekt avtomatik "yangilanuvchi rasm" rejimiga tushadi.
MONTHLY_BUDGET_MIN = 600


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
                            besides: str = "") -> bool:
        """Oqimni to'xtatadi — FAQAT boshqa ko'ruvchi qolmagan bo'lsa.

        Oqim kalit `{seriya}:{kanal}` bo'yicha yagona: bitta kanalni ikki
        operator ko'rsa, ikkalasi AYNI oqimdan foydalanadi. Shuning uchun
        birovning seansi yopilganda darrov `stop_stream` yuborib bo'lmaydi —
        aks holda ikkinchi operatorning videosi sababsiz o'chadi.

        Jonli sinovda AYNAN shu sodir bo'ldi: eskirgan seans tozalanганda
        o'sha kanaldagi YANGI, faol oqim ham o'chdi.
        """
        qolgan = [s for s in gw.db.open_stream_sessions(agent_id)
                  if s["channel"] == channel and s["session_id"] != besides]
        if qolgan:
            log.info("kanal %s da yana %d ko'ruvchi bor — oqim to'xtatilmaydi",
                     channel, len(qolgan))
            return False
        await _agent_command(agent_id, "stop_stream", {"channel": channel}, actor)
        return True

    # ------------------------------------------------ eskirgan seanslar

    async def reap_sessions() -> int:
        """Brauzer aloqasi uzilgan seanslarni yopadi va oqimni to'xtatadi.

        BU FUNKSIYA MUHIM: usiz unutilgan sahifa obyektning uplink'ini
        soatlab band qiladi va 4-prinsip buziladi (rasm kechikadi).
        """
        yopilgan = 0
        for seans in gw.db.stale_stream_sessions(LEASE_S):
            gw.db.end_stream_session(seans["session_id"], "brauzer javob bermadi")
            await _stop_if_last(seans["agent_id"], seans["channel"], "tizim")
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
        if getattr(gw, "_stream_reaper", None) is not None:
            return
        try:
            gw._stream_reaper = asyncio.get_running_loop().create_task(reaper_loop())
        except RuntimeError:          # hodisa tsikli yo'q (test/sinxron chaqiruv)
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
                "publish_url": media.publish_url(agent_id, kanal),
                "duration_s": AGENT_DURATION_S,
            }, actor)
        if format == "json":
            # To'r sahifasi sahifani almashtirmasdan oqim ochadi.
            return {"session": session_id, "mode": rejim, "channel": kanal}
        return RedirectResponse(
            f"/admin/agent/{agent_id}/stream/{kanal}?s={session_id}",
            status_code=303)

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
            await _stop_if_last(seans["agent_id"], seans["channel"], "tizim")
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
                                                 seans["channel"]),
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
        await _stop_if_last(seans["agent_id"], seans["channel"], _actor(request))
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
        url = media.whep_url(seans["agent_id"], seans["channel"])
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

        kataklar, kanallar = [], []
        for nvr in nvrs:
            for c in nvr.get("channels") or []:
                if not c.get("enabled", True):
                    continue
                ch = int(c.get("id", 0))
                kanallar.append(ch)
                kataklar.append(
                    f"<div class='cam' data-ch='{ch}'>"
                    f"<div class='camview'>"
                    f"<video muted playsinline autoplay></video>"
                    f"<button class='play' title='jonli ko`rish'>&#9654;</button>"
                    f"<span class='badge'></span></div>"
                    f"<div class='camcap'><b>{ch}</b> "
                    f"{esc(c.get('name'))}</div></div>")

        body = f"""<h1>{esc(agent.get('market_name'))} — barcha kameralar</h1>
<p class="hint"><a href="/admin/agent/{esc(agent_id)}">&larr; obyekt sahifasi</a>
&middot; {len(kanallar)} ta kamera &middot; jonli video bir vaqtda
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
    {"agent": agent_id, "channels": kanallar, "limit": limit})}</script>"""

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
  var jonlilar = {};                    // kanal -> {pc, session}

  function katak(ch) {
    return document.querySelector('.cam[data-ch="' + ch + '"]');
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
    var fd = new FormData();
    fd.append('channel', ch);
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
    var ch = el.getAttribute('data-ch');
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
