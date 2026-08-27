# =============================================================================
# ILOVA MARSHRUTLARI — DEV VA PRODUCTION UCHUN YAGONA MANBA.
#
# Bu fayl ikkala konfiguratsiyaga ham `include` qilinadi:
#   ops/nginx/nginx.conf                (dev, faqat :80)
#   ops/nginx/templates/prod.conf.template (production, TLS bilan)
#
# NEGA NUSXA EMAS, INCLUDE: bu yerda go2rtc API'sining ikki qatlamli
# taqiqi, `auth_request` bilan bozorga tegishlilik tekshiruvi va
# X-Forwarded-For ning OVERWRITE qoidasi yashaydi. Nusxa qilinsa,
# birida tuzatilgan xavfsizlik xatosi ikkinchisida jimgina qolardi.
# =============================================================================

# =============================================================================
# ⛔⛔ UPSTREAM NOMLARI HAR SO'ROVDA QAYTA YECHILADI (260818, jonli 502).
# =============================================================================
# nginx `proxy_pass http://core-api:8000;` deb yozilganda nomni FAQAT ISHGA
# TUSHGANDA yechadi va IP'ni umrbod keshda saqlaydi. Docker'da konteyner
# qayta yaratilganda IP O'ZGARADI — natijada nginx o'lik manzilga urinadi.
#
# O'LCHANGAN: `docker compose up -d` core-api'ni qayta yaratdi
# (172.19.0.8 -> 172.19.0.9); nginx eski IP'ga urinib BUTUN saytga 502
# berdi, `docker compose ps` esa hammasini «healthy» ko'rsatdi va
# core-api ichkaridan `/healthz` ga 200 qaytarardi. Ya'ni production'da
# har deploydan keyin sayt jimgina o'lardi va sabab hech qayerda
# ko'rinmasdi (brauzerda 502, jurnalda esa eski IP).
#
# ⛔ YECHIM: Docker'ning ichki DNS'i (127.0.0.11) + `proxy_pass` da
#    O'ZGARUVCHI. O'zgaruvchi bo'lgani uchun nginx nomni HAR SO'ROVDA
#    yechadi, `valid=10s` esa keshni 10 sekundda chegaralaydi.
#
# ⚠ `ipv6=off` MAJBURIY: Docker DNS AAAA yozuvini bermaydi va usiz har
#   yechish 5 s kutib turardi.
#
# ⚠ `proxy_pass` da URI QISMI YO'Q — shuning uchun o'zgaruvchi shaklda ham
#   asl (yoki `rewrite` dan keyingi) URI uzatiladi, xulq O'ZGARMAYDI.
resolver 127.0.0.11 valid=10s ipv6=off;
set $up_core     core-api;
set $up_frontend frontend;
set $up_go2rtc   go2rtc;
# CamAgent gateway — IXTIYORIY servis (compose.camagent.yml). O'zgaruvchili
# `proxy_pass` tufayli servis ko'tarilmagan bo'lsa ham nginx ishga tushadi,
# o'sha yo'l esa 502 qaytaradi (yuqoridagi 260818 izohidagi mexanizm).
set $up_camagent camagent-gateway;

    client_max_body_size 20m;

    # --- D-11, 1-blok: go2rtc API'sining to'g'ridan-to'g'ri yo'li ---
    location ~ ^/(api/streams|api/config|api/restart) {
        return 403;
    }

    # --- D-11, 2-blok: o'sha API'ning `/live/` orqali yo'li ---
    location ~ ^/live/api/(streams|config|restart) {
        return 403;
    }

    # --- Jonli ko'rish: avtorizatsiya nginx'da, media go2rtc'dan ---
    #
    # `auth_request` HAR SO'ROVDA `core-api` ga boradi va u faqat STATUSGA
    # qaraydi (204 -> o'tkazadi, 403 -> rad etadi). go2rtc'da bozor
    # tushunchasi YO'Q — unda faqat global Basic-auth bor, ya'ni uni
    # to'g'ridan-to'g'ri ochish A bozori direktoriga B bozori kamerasini
    # berardi (T-03-46).
    #
    # Ro'yxat ATAYIN qisqa: `api/ws` — WebRTC/MSE signalling, qolgani HLS
    # zaxira yo'li. `frame.jpeg` 4-fazadagi kadr olish uchun EMAS (u ichki
    # tarmoqdan boradi) — u dala diagnostikasi uchun.
    location ~ ^/live/(api/ws|api/webrtc|api/frame\.jpeg|api/stream\.m3u8|api/hls/.+)$ {
        auth_request /internal/live-authz;

        rewrite ^/live/(.*)$ /$1 break;
        proxy_pass http://$up_go2rtc:1984;
        proxy_http_version 1.1;

        # WebSocket signalling (WebRTC va MSE ikkalasi ham `/api/ws` dan).
        proxy_set_header Upgrade    $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host       $host;

        # Jonli oqim uzoq ochiq turadi — standart 60 s uni har daqiqada
        # uzardi va UI buni "tarmoq nosozligi" deb ko'rsatardi.
        proxy_read_timeout 3600s;
        proxy_buffering off;
    }

    # --- `auth_request` NISHONI — FAQAT ICHKI SUBSO'ROV ---
    #
    # `internal;` bu yo'lni tashqi so'rov uchun 404 qiladi. Bu ikkinchi
    # qatlam: marshrutning O'ZI ham tokensiz so'rovga 403 beradi
    # (`app/api/internal/live_authz.py`), ya'ni himoya nginx
    # konfiguratsiyasiga BOG'LIQ EMAS.
    #
    # `X-Original-URI` — asl so'rovning TO'LIQ yo'li (query bilan): token
    # ham, `src` ham o'sha yerda va `core-api` ikkalasining MOSLIGINI
    # tekshiradi. Tana uzatilmaydi (`GET` subso'rovida u baribir yo'q).
    location = /internal/live-authz {
        internal;
        proxy_pass http://$up_core:8000/internal/live-authz;
        proxy_pass_request_body off;
        proxy_set_header Content-Length "";
        proxy_set_header X-Original-URI $request_uri;
    }

    # --- CamAgent: tunnelsiz bozor agentlarining kirish nuqtasi ---
    #
    # `/api/` dan UZUNROQ prefiks — nginx eng uzun mosini tanlaydi, ya'ni
    # bu yo'l hech qachon core-api'ga tushmaydi va core-api'ning marshrut
    # darvozalariga (cross-tenant matritsasi) umuman ko'rinmaydi.
    # Protokol (muzlatilgan): services/camagent-gateway/docs/protocol.md —
    # `/ws` (WebSocket: register/heartbeat/buyruqlar), `/snapshot` (JPEG),
    # `/activate`, `/speedtest`. Agent FAQAT tashqaridan o'zi ulanadi.
    location /api/v1/agent/ {
        proxy_pass http://$up_camagent:8787;
        proxy_http_version 1.1;

        # WebSocket boshqaruv kanali (`/ws`). Oddiy POST'larga bu ikki
        # sarlavha xalal bermaydi — `location /` (frontend) bilan bir xil
        # naqsh.
        proxy_set_header Upgrade    $http_upgrade;
        proxy_set_header Connection "upgrade";

        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        # OVERWRITE (fayl boshidagi izohga qarang) — barcha location'lar
        # BIR XIL bo'lishi shart, aks holda soxtalashtirish yo'li ochilardi.
        proxy_set_header X-Forwarded-For   $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Kadr chegarasi serverda 25 MB (haqiqiylari ~40 KB) — server
        # darajasidagi 20m shu yo'l uchun kengaytiriladi, nginx to'siq
        # bo'lib qolmasin.
        client_max_body_size 30m;
        # WS'da har 60 s heartbeat + 30 s protokol ping'i yuradi — 300 s
        # jimlik faqat o'lik ulanishda bo'ladi.
        proxy_read_timeout 300s;
    }

    # --- CamAgent operator paneli (260828) ---
    #
    # NEGA KERAK: aktivatsiya kodi va kadr olish jadvali shu yerdan
    # kiritiladi. Busiz har amal uchun serverga SSH bilan kirish kerak
    # bo'lardi va 12 bozorli ish jarayonida bu real to'siq.
    #
    # ⛔ HIMOYA — GATEWAY KALITI (`CAMAGENT_GW_ADMIN_TOKEN`, 24 bayt),
    #    sbozor sessiyasi EMAS. Ikkalasini bog'lash uchun `auth_request`
    #    kerak, u esa gateway'ni core-api'ning rol modeliga bog'lardi —
    #    CamAgent atayin mustaqil (u boshqa loyihalarda ham ishlaydi).
    #    Kalitsiz so'rov 401 oladi va gateway xato urinishlarni IP bo'yicha
    #    cheklaydi (`PANEL_MAX_TRIES`).
    #
    # ⚠ PREFIKS `rewrite` BILAN OLIB TASHLANADI, `proxy_pass` oxiridagi
    #   `/` BILAN EMAS. Sabab nginx'ning qoidasida: `proxy_pass` da
    #   O'ZGARUVCHI ishlatilganda (`$up_camagent` — servis ko'tarilmagan
    #   bo'lsa ham nginx ishga tushsin degan qaror) URI qismi E'TIBORGA
    #   OLINMAYDI va so'rov gateway'ga `/camagent/admin` ko'rinishida
    #   yetib borardi — ya'ni 404, lekin nginx'dan emas, gateway'dan.
    #   [260828 da aynan shu o'lchandi.]
    #
    # ⛔ HAVOLALAR QAYTA YOZILADI (`sub_filter`). Gateway HTML'i o'zining
    #    yo'llarini `/admin/...` deb yozadi — u prefiks ortida turganini
    #    bilmaydi. Qayta yozilmasa bosh sahifa ochilardi, ichidagi har
    #    havola esa sbozor frontendiga tushib 404 berardi: eng yomon shakl,
    #    chunki «ishlayapti» ga o'xshaydi.
    #
    #    Muqobil — gateway'ga `root_path` berib 61 ta havolani kod ichida
    #    prefiksli qilish. U CamAgent'ni sbozor'ning joylashuv qaroriga
    #    bog'lab qo'yardi, holbuki u boshqa loyihalarda ham ishlaydi.
    #
    # ⚠ `Accept-Encoding` TOZALANADI: `sub_filter` gzip'langan javobni
    #   ko'ra olmaydi va jimgina hech narsa almashtirmasdi. Panel sahifasi
    #   kichik, siqilmagani sezilmaydi.
    location /camagent/ {
        rewrite ^/camagent/(.*)$ /$1 break;
        proxy_pass http://$up_camagent:8787;
        proxy_http_version 1.1;

        # `sub_filter_types` YOZILMAYDI: `text/html` standartda allaqachon
        # bor va uni takrorlash nginx'ni har reload'da ogohlantirishga
        # majbur qilardi (o'lchandi 260828).
        proxy_set_header Accept-Encoding "";
        sub_filter_once off;
        sub_filter 'href="/admin'   'href="/camagent/admin';
        sub_filter 'action="/admin' 'action="/camagent/admin';
        sub_filter 'href="/live'    'href="/camagent/live';

        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Jonli video (WHEP) va panel ichidagi kamera devori uchun.
        proxy_set_header Upgrade    $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 300s;
    }

    location /api/ {
        proxy_pass http://$up_core:8000;
        proxy_http_version 1.1;

        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        # OVERWRITE (fayl boshidagi izohga qarang) — `$proxy_add_x_forwarded_for`
        # mijozga zanjirning chap tomonini yozish imkonini berardi.
        proxy_set_header X-Forwarded-For   $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://$up_frontend:3000;
        proxy_http_version 1.1;

        # Next.js dev/HMR va kelajakdagi WebSocket oqimlari uchun.
        proxy_set_header Upgrade           $http_upgrade;
        proxy_set_header Connection        "upgrade";

        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        # OVERWRITE (fayl boshidagi izohga qarang) — ikkala location BIR XIL
        # bo'lishi shart, aks holda frontend yo'li orqali soxtalashtirish ochiq
        # qolardi.
        proxy_set_header X-Forwarded-For   $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
