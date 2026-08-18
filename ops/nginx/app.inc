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
        proxy_pass http://go2rtc:1984;
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
        proxy_pass http://core-api:8000/internal/live-authz;
        proxy_pass_request_body off;
        proxy_set_header Content-Length "";
        proxy_set_header X-Original-URI $request_uri;
    }

    location /api/ {
        proxy_pass http://core-api:8000;
        proxy_http_version 1.1;

        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        # OVERWRITE (fayl boshidagi izohga qarang) — `$proxy_add_x_forwarded_for`
        # mijozga zanjirning chap tomonini yozish imkonini berardi.
        proxy_set_header X-Forwarded-For   $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://frontend:3000;
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
