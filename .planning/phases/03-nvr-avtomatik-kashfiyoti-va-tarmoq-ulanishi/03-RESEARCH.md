# Faza 3: NVR avtomatik kashfiyoti va tarmoq ulanishi — Tadqiqot

**Tadqiqot sanasi:** 2026-08-02
**Domen:** Hikvision ISAPI qurilma kashfiyoti, RTSP→WebRTC jonli oqim, WireGuard split-tunnel, simulyator-birinchi test
**Ishonch darajasi:** MEDIUM-HIGH (ISAPI endpointlari va simulyator yo'li HIGH; real qurilma xulqi — o'lchanmagan, LOW)

> **HOLAT: TO'LIQ.** Barcha bo'limlar (A–E) yozilgan.

---

## Xulosa

Bu faza **texnologiya tanlash fazasi emas** — stek CLAUDE.md'da qulflangan (go2rtc, `httpx.DigestAuth`, `cryptography` Fernet, WireGuard split-tunnel) va bu tadqiqot ularni qayta muhokama qilmaydi. Butun risk **ikkita joyda**: (1) real Hikvision NVR'ga hech qachon ulanmagan holda "kashfiyot ishlaydi" deb aytish, va (2) `[ASSUMED]` bo'lgan ISAPI tafsilotlarini simulyatorga ko'chirib, **o'z taxminimizni o'zimiz tasdiqlab qo'yish** (simulator-confirms-itself antipattern). Ikkinchisi birinchisidan xavfliroq, chunki u yashil CI beradi.

Beshta topilma rejaga bevosita ta'sir qiladi. **Birinchi:** NVR'da kanallarni sanash uchun **`/ISAPI/ContentMgmt/InputProxy/channels` avtoritetli**, `/ISAPI/System/Video/inputs/channels` emas — birinchisi NVR ortidagi haqiqiy IP-kameralarni (IP, model, nom) beradi, ikkinchisi NVR'ning o'z video-kirish slotlarini sanaydi va bo'sh slotlarni ham "kanal" deb ko'rsatadi. Standalone IP-kamerada esa `InputProxy` **umuman yo'q** (404) — shuning uchun kashfiyot `/ISAPI/System/deviceInfo` dagi `<deviceType>` ga qarab ikki yo'lga bo'linadi [VERIFIED: hikvision_next `DS-7616NI-K2.json` fixture]. **Ikkinchi:** RTSP porti **taxmin qilinmaydi** — `/ISAPI/Security/adminAccesses` `AdminAccessProtocolList` ichida `protocol=RTSP` + `portNo` ni beradi; 554 faqat *fallback*. **Uchinchi:** takroriy skanerlashning barqaror kaliti — **`(nvr_device_id, channel_no)`**, kamera seriyasi emas: NVR'ning o'zi RTSP URL'ni aynan kanal raqami bilan adreslaydi, ya'ni boshqa kalit tanlash URL'ni identifikatordan uzib qo'yardi. Kamera IP'si/modeli esa **kuzatiladigan atribut** bo'lib saqlanadi va o'zgarsa audit yozuvi tug'diradi (fizik almashtirish signali). **To'rtinchi:** SC#3 talab qilgan "aniq xato sababi" **javob kodidan chiqmaydi** — parol xato ham, soat farqi ham, qulflangan hisob ham `401` beradi. Ularni ajratish uchun uchta qo'shimcha signal kerak: javob tanasidagi `<lockStatus>`/`<unlockTime>` XML'i, `WWW-Authenticate` sarlavhasining `stale` bayrog'i, va **`Date` sarlavhasi bilan mahalliy soatni solishtirish** — oxirgisi qurilma soat farqini *401 dan oldin* aniqlaydigan yagona ishonchli usul. **Beshinchi:** sessiya limiti CLAUDE.md'dagi "6–16" dan murakkabroq — Hikvision hujjati **128 ta "remote connection"** deydi, lekin amaldagi to'siq deyarli har doim **chiquvchi bitreyt (outgoing bandwidth)**, ulanish soni emas; 25 ta asosiy oqim (4 MP × 25) NVR'ning 32–160 Mbps chiqish byudjetini yeb qo'yadi. Shuning uchun arxitektura qarori: **go2rtc faqat sub-oqimga ulanadi**, asosiy oqim esa faqat talab bo'yicha va bittalab.

Simulyator (CAM-09) — fazaning **eng katta noma'lumi va eng katta qiymati**. Tavsiya: **maxsus FastAPI ISAPI-mock** (yangi servis EMAS — `services/nvr-sim/`, faqat `sim` compose profilida) + **go2rtc'ning o'zi** RTSP manbai sifatida (`ffmpeg:...#loop`). Tayyor "Hikvision emulyatori" loyihasi yo'q — qidiruv faqat ONVIF emulyatorlarini va yagona-endpointli mocklarni topdi. Bu **yaxshi xabar**, chunki mockning qiymati aynan **xato yo'llarini** ishonchli qayta tug'dirishida (noto'g'ri parol, soat farqi, offline kanal, sessiya limiti) — bu tayyor emulyatorda baribir bo'lmasdi. Muhim shart: mockning javoblari **yozib olingan haqiqiy XML** dan kelishi kerak (`hikvision_next` repozitoriyasidagi `DS-7616NI-K2.json` / `DS-7732NI-M4.json` fixture'lari — real qurilmalardan olingan), qo'lda yozilgan "shunga o'xshash" XML dan emas.

**Primary recommendation:** Kashfiyotni **`arq` jobi** sifatida quring (inline emas — 25 kanal × Digest handshake × timeout budjeti so'rov chegarasidan oshadi), natijani `nvr_discovery_runs` jadvalida holat bilan saqlang va frontend uni poll qilsin. Kanal identifikatorini `(nvr_id, channel_no)` qiling. Parolni `cryptography` Fernet bilan shifrlab **alohida ustunda** saqlang va uni **hech qachon** javob sxemasiga qo'ymang (Pydantic response modelida maydon **umuman bo'lmasin** — `exclude` emas). Simulyatorni real fixture XML'idan quring va **har bir xato yo'li uchun alohida sim-endpoint bayrog'i** bering. WireGuard'ni `network_mode: host` sidecar sifatida ishlating va tunnel-yagona-yo'l da'vosini **konteyner tarmoq qoidasi** bilan isbotlang, tunnelni o'chirib emas.

---

## User Constraints (CONTEXT.md dan)

**CONTEXT.md bu faza uchun MAVJUD EMAS** (`has_context: false`). Ya'ni bu tadqiqot qulflangan foydalanuvchi qarorlari bilan cheklanmagan — uning o'rniga **ROADMAP.md ning "Mahsulot qoidasi: self-service onboarding (MAJBURIY)" bo'limi** va **Phase 3 Success Criteria** majburiy kirish sifatida qabul qilinadi.

### Majburiy mahsulot qoidasi (ROADMAP.md, 2026-08-01 da o'rnatilgan)

> **Admin saytda faqat kerakli ma'lumotni kiritadi — tizim qolganini o'zi, xatosiz bajaradi.**

| Onboarding qadami | Admin nima kiritadi | Tizim nima qiladi |
|---|---|---|
| **Kameralar** | **NVR manzili + login/parol** | ISAPI orqali qurilmani aniqlaydi, kanallarni sanaydi, **kameralarni avtomat qo'shadi** — qo'lda kamera kiritish YO'Q |

Uchta oqibati **majburiy**:

1. **Muhandis aralashuvi bilan ishlaydigan onboarding qabul qilinmaydi.** Yangi bozor kod yozmasdan, skript ishlatmasdan, SSH'siz ulanadi.
2. **Tashqi bog'liqlik hech qachon `Blocks:` bo'lmaydi.** Kelmagan uskuna fazani to'xtatmaydi — u keyin to'ldiriladigan **ma'lumot** sifatida modellashtiriladi.
3. **Tekshiruv simulyator ustida bajariladigan qilib loyihalanadi.** Real qurilmaga o'tish **sozlama o'zgarishi** bo'ladi, qayta loyihalash emas.

### Faza Success Criteria (ROADMAP.md → Phase 3) — darvoza sifatida

| # | Mezon |
|---|-------|
| SC#1 | Admin **faqat** NVR manzili + login/parol kiritadi → tizim modelni aniqlaydi, kanallarni sanaydi, har biriga kamera yozuvi (nom, kanal, asosiy/sub URL) **avtomat** yaratadi — qo'lda birorta RTSP URL yozilmaydi |
| SC#2 | Qayta skanerlash **idempotent**: yangi kanal qo'shiladi, yo'qolgani `offline`, mavjudi tegilmaydi — dublikat yo'q |
| SC#3 | Ulanish xatosi **sababi va tuzatish yo'li** bilan: parol xato / soat >5 daq / firmware `digest/basic` / kanal offline / sessiya limiti — "ulanmadi" **qabul qilinmaydi** |
| SC#4 | RTSP login/parollari bazada **Fernet** bilan shifrlangan; parol **hech qachon** API javobida yoki jurnalda ko'rinmaydi |
| SC#5 | Server NVR'ga **faqat WireGuard** orqali kiradi; tunnel o'chsa ulanish uziladi; NVR internetdan to'g'ridan-to'g'ri ochiq emas |
| SC#6 | Direktor **avtorizatsiyadan keyin** jonli tasvirni ko'radi; avtorizatsiyasiz to'g'ridan-to'g'ri havola **ishlamaydi** |
| SC#7 | **Butun oqim real uskunasiz, simulyatsiya qilingan NVR ustida uchidan-uchiga ishlaydi va CI'da o'lchanadi** |

### Claude ixtiyorida (bu tadqiqot tavsiya beradi)

Kashfiyot mexanizmi (inline vs `arq`), ma'lumot modeli shakli, simulyator arxitekturasi, xato taksonomiyasining aniq kodlari, go2rtc'ni dinamik sozlash usuli, WireGuard konteyner topologiyasi.

### Bu fazada QURILMAYDI (Scope Fence — pastdagi bo'limga qarang)

Snapshot jadvali va kadr olish (4-faza), kamera-zona poligonlari (5-faza), CV (5-faza).

---

## Phase Requirements

| ID | Tavsif (REQUIREMENTS.md dan) | Tadqiqot qaysi topilma bilan qo'llab-quvvatlaydi |
|----|------------------------------|--------------------------------------------------|
| **CAM-01** | Bozor admini kameralarni qo'shadi/sozlaydi; RTSP ma'lumotlari **shifrlangan** saqlanadi; "ulanishni tekshirish" tugmasi ishlaydi | **C.10** (Fernet naqshi, kalit manbai, javob/jurnal darvozasi) · **A.3** (ulanish testining xato taksonomiyasi) · **E.15** (`nvr_devices` sxemasi) |
| **CAM-02** | Server NVR'ga **faqat WireGuard** orqali kiradi; NVR internetga to'g'ridan-to'g'ri ochilmaydi | **C.11** (split-tunnel `AllowedIPs`, `network_mode: host` sidecar, isbot testi) · **C.12** (CGNAT, `PersistentKeepalive`) |
| **CAM-03** | Direktor/admin panelda **jonli** kamera tasvirini ko'radi (go2rtc, **avtorizatsiya ortida**) | **D.13** (go2rtc'ni proxy ortiga yashirish, imzolangan qisqa muddatli token, WebRTC vs HLS/MSE) · **D.14** (sessiya byudjeti) |
| **CAM-08** | Admin **faqat** manzil+parol kiritadi; ISAPI orqali qurilma aniqlanadi, kanallar sanaladi, kameralar avtomat yaratiladi; qayta skan **idempotent**; xato **sababi+yechimi** bilan | **A.1** (endpoint tanlovi va avtoritetlik) · **A.2** (RTSP URL hosil qilish + port kashfiyoti) · **A.3** (xato taksonomiyasi) · **A.4** (idempotentlik kaliti) · **E.16** (`arq` jobi) |
| **CAM-09** | Simulyatsiya qilingan Hikvision NVR (**ISAPI mock + go2rtc RTSP manbai**) compose profili sifatida; kashfiyot, ulanish testi, jonli ko'rish va kadr olish yo'li real uskunasiz uchidan-uchiga ishlaydi va **CI'da o'lchanadi** | **B.6** (arxitektura tanlovi va sabab) · **B.7** (minimal ISAPI yuzasi) · **B.8** (xato rejimlari) · **B.9** (compose profili, CI, video manbai) |

---

## Architectural Responsibility Map

| Qobiliyat | Asosiy qatlam | Ikkinchi qatlam | Sabab |
|-----------|---------------|-----------------|-------|
| NVR bilan HTTP muloqoti (Digest, ISAPI) | **core-api (`app/services/isapi/`)** | — | 3 ta servis cheklovi: yangi "nvr-service" YO'Q. cv-service faqat 4-fazada ISAPI zaxira yo'li uchun kerak bo'ladi |
| Kanallarni sanash va kamera yozuvi yaratish | **core-api + navbat worker'i** | Database (idempotent `ON CONFLICT`) | 25 kanal × Digest handshake HTTP so'rov byudjetiga sig'maydi (**E.16**) |
| Kashfiyot natijasining **idempotentligi** | **Database (`UNIQUE (market_id, nvr_id, channel_no)`)** | API (`ON CONFLICT DO UPDATE`) | "Dublikat hech qachon" kafolati faqat DB konstraytida bo'ladi — 2-faza `stall_code_registry` falsafasi |
| NVR parolining maxfiyligi | **Application (Fernet, `cryptography`)** | Database (RLS) · Logging (`censor_secrets`) | Postgres'da `pgcrypto` kaliti DB ichida bo'lardi; SC#4 aynan "bazaga kirgan odam ko'rmasin" deydi |
| Parolning javobga chiqmasligi | **API (Pydantic response modelida maydon YO'Q)** | Test (`test_no_secret_in_response`) | `exclude=True` unutiladi; maydonning umuman bo'lmasligi — strukturaviy kafolat |
| RTSP URL hosil qilish | **Application (sof funksiya)** | — | DB'da faqat komponentlar (`host`, `port`, `channel_no`); URL **hosila** — parol o'zgarganda migratsiya kerak emas |
| Tarmoq izolyatsiyasi (NVR faqat tunnel orqali) | **Infra (WireGuard sidecar + Docker network)** | Ops (`AllowedIPs` konfiguratsiyasi) | Ilova qatlamida "faqat VPN orqali" ni majburlab bo'lmaydi |
| RTSP→WebRTC/HLS transkodsiz uzatish | **go2rtc** | Nginx (HTTP proxy) | CLAUDE.md'da qulflangan; qayta yozilmaydi |
| Jonli ko'rishga **avtorizatsiya** | **core-api (qisqa muddatli imzolangan token)** | Nginx (`auth_request` yoki proxy) | go2rtc'da tenant tushunchasi YO'Q — u autentifikatsiyani biladi, avtorizatsiyani emas (**D.13**) |
| go2rtc'da oqim ro'yxatga olish | **core-api → go2rtc HTTP API** | Config fayl (bootstrap) | Kamera kashf qilinganda **restart'siz** qo'shilishi kerak (**D.13**) |
| Simulyatsiya qilingan NVR | **`services/nvr-sim/` (FastAPI, `sim` profili)** | go2rtc (RTSP manbai) | Prodga **hech qachon** chiqmaydi; profil ortida |
| Audit (rekvizit o'zgarishi, kashfiyot, jonli ko'rish) | **Database (`fn_audit_row()` trigger)** | API (`audit_read` jonli ko'rish uchun) | 1-faza D-10: xom SQL yo'li ham qamraladi |

---

## Project Constraints (CLAUDE.md dan)

Quyidagilar **majburiy** va rejada qayta muhokama qilinmaydi. Bu fazaga tegishlilari:

| Direktiva | Bu fazada nimani anglatadi |
|-----------|----------------------------|
| **Servislar soni aynan 3** (`core-api`, `cv-service`, `bot-service`) | ISAPI klienti — `core-api` ichida. `nvr-sim` **mahsulot servisi emas**, `sim` compose profilidagi test uskunasi — 3 ta cheklovni buzmaydi (xuddi `tests` konteyneri kabi) |
| **go2rtc v1.9.14** jonli ko'rish uchun qat'iy | Jonli ko'rish qayta o'ylanmaydi. WebRTC uchun **UDP 8555** to'g'ridan-to'g'ri ochiladi (HTTP proxy'dan o'tmaydi) |
| **Snapshot: go2rtc `/api/frame.jpeg` → ISAPI `/picture` → ffmpeg** | Bu **4-faza**. 3-fazada faqat `/picture` ulanish testining bir qismi sifatida bir marta chaqiriladi |
| **`httpx` 0.28.1 + `httpx.DigestAuth`** | ISAPI klienti. Yangi HTTP kutubxonasi qo'shilmaydi |
| **`cryptography` 49.0.0** (allaqachon `pyproject.toml` da) | Fernet — **yangi paket kerak emas** |
| **`tenacity` 9.1.4** so'rov ichidagi retry uchun | ISAPI chaqiruvlarining qayta urinishi. `arq` job-darajasidagi retry'dan **boshqa qatlam** |
| **`arq` 0.28.0** navbat/cron uchun | ⛔ **BU FAZADA ISHLAMAYDI** — `arq 0.28.0` `redis<6` talab qiladi, `core-api` esa `redis==8.0.1` da. Empirik tasdiqlandi (E.16). O'rniga **`taskiq` + `taskiq-redis`** (CLAUDE.md ning o'zi sanksiyalagan muqobil) |
| **WireGuard split-tunnel: `AllowedIPs` faqat NVR subneti, `0.0.0.0/0` HECH QACHON** | `ops/wireguard/` konfiguratsiyasi; to'liq tunnel VPS'ning butun chiqishini bozor DSL'idan o'tkazardi |
| **NVR internetga port-forward QILINMAYDI** | Ulanish faqat tunnel ichidan |
| **RTSP parollari Fernet bilan shifrlangan** | SC#4 |
| **`float` pul uchun TAQIQLANGAN / naive datetime TAQIQLANGAN** | Bu fazada pul yo'q; `timestamptz` + `ZoneInfo("Asia/Tashkent")` |
| **Testlarda SQLite TAQIQLANGAN** | RLS — faqat haqiqiy `postgres:18.4` + testcontainers |
| **`uv` per-service `pyproject.toml`** | Yangi paketlar faqat `services/core-api/pyproject.toml` ga |
| **AGPL TAQIQLANGAN** (tijoriy SaaS) | Simulyator uchun **MediaMTX** (MIT) mumkin, lekin go2rtc allaqachon bor — yangi bog'liqlik kiritilmaydi. `onvif-zeep` oilasidan foydalanilmaydi |
| **Apple-uslub minimal dizayn; 3 til majburiy** | Kashfiyot sahifasi va xato xabarlari **uchala tilda** — SC#3 xato matnlari i18n kalitlari bo'ladi, qotib qolgan matn emas |
| **GSD Workflow Enforcement** | Fayl o'zgartirish faqat GSD komandasi ichida |

---

## A. Hikvision ISAPI kashfiyoti

### A.1 — Qurilmani aniqlash va kanallarni sanash: qaysi endpoint avtoritetli?

Kashfiyot **ikki bosqichli** bo'ladi va bosqichlar orasidagi tarmoqlanish `deviceType` ga tayanadi.

#### 1-qadam — qurilma pasporti (har doim, birinchi chaqiruv)

```
GET /ISAPI/System/deviceInfo
```

Real NVR javobi (`hikvision_next` repozitoriyasidagi **yozib olingan** fixture, `DS-7616NI-K2`) [VERIFIED: github.com/maciej-or/hikvision_next/tests/fixtures/devices/DS-7616NI-K2.json]:

```xml
<DeviceInfo version="1.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">
  <deviceName>NVR</deviceName>
  <deviceID>48473931-3030-0000-0000-acb00f0000bd</deviceID>
  <model>DS-7616NI-K2</model>
  <serialNumber>DS-7616NI-K20000000000CCRRG00000000WCVU</serialNumber>
  <macAddress>87:02:30:0a:c5:06</macAddress>
  <firmwareVersion>V4.74.210</firmwareVersion>
  <firmwareReleasedDate>build 240108</firmwareReleasedDate>
  <encoderVersion>V5.0</encoderVersion>
  <deviceType>NVR</deviceType>
  <hardwareVersion>B-R-K51-00</hardwareVersion>
  <manufacturer>hikvision</manufacturer>
</DeviceInfo>
```

Bu javobning to'rtta maydoni rejaga bevosita kiradi:

| Maydon | Nima uchun kerak |
|--------|------------------|
| `<deviceType>` | **Tarmoqlanish nuqtasi**: `NVR`/`DVR`/`HDVR` → `InputProxy` yo'li; `IPCamera`/`IPDome` → standalone yo'li |
| `<model>` | UI'da ko'rsatiladi ("DS-7616NI-K2 topildi, 6 ta kamera") — SC#1 ning "qurilma modelini aniqlaydi" qismi |
| `<serialNumber>` | **NVR'ning barqaror identifikatori** — IP o'zgarganda ham u o'sha qurilma ekanini bilish uchun |
| `<firmwareVersion>` | Xato diagnostikasi va kelajakdagi firmware-bo'yicha tarmoqlanish |

⚠ **XML namespace majburiy:** javob `xmlns="http://www.hikvision.com/ver20/XMLSchema"` bilan keladi. Namespace'siz `ElementTree.find("deviceType")` **`None` qaytaradi** va parser jimgina bo'sh natija beradi. Parser namespace-agnostik bo'lishi kerak (yorliqdan `{...}` prefiksini olib tashlash) — bu **eng ko'p uchraydigan integratsiya xatosi**. [VERIFIED: fixture XML]

#### 2-qadam-A — NVR bo'lsa: `InputProxy` (AVTORITETLI)

```
GET /ISAPI/ContentMgmt/InputProxy/channels          # kanal ro'yxati + manba tavsifi
GET /ISAPI/ContentMgmt/InputProxy/channels/status   # kanal onlayn holati
```

Javob shakli — `<InputProxyChannelList>` ichida `<InputProxyChannel>` elementlari; har birida `<id>`, `<name>` va `<sourceInputPortDescriptor>` (ichida `proxyProtocol`, `addressingFormatType`, `ipAddress`, `managePortNo`, `srcInputPort`, `userName`, `streamType`) [VERIFIED: `hikvision_next` DS-7616NI-K2 fixture — 6 ta kamera IP va model bilan; CITED: eu-evops/homebridge-hikvision `HikvisionApi.ts`].

`.../status` esa har kanal uchun `<online>true|false</online>` beradi va `id` bo'yicha birinchi ro'yxatga qo'shiladi — `homebridge-hikvision` aynan shu naqshni ishlatadi: *"status is joined by matching channel ID; online status filtered to return only cameras where `status.online === 'true'`"* [CITED: github.com/eu-evops/homebridge-hikvision].

**Nega bu avtoritetli:**

| Endpoint | NVR'da nima qaytaradi | Kashfiyot uchun yaroqlimi |
|----------|----------------------|---------------------------|
| **`/ISAPI/ContentMgmt/InputProxy/channels`** | NVR ortiga **haqiqatan ulangan** IP-kameralar: nom, kamera IP'si, manba porti, model | ✅ **AVTORITETLI** — faqat mavjud kameralar |
| `/ISAPI/ContentMgmt/InputProxy/channels/status` | Har kanalning onlayn/oflayn holati | ✅ **Majburiy juftlik** — SC#2 dagi `offline` belgisi shundan |
| `/ISAPI/System/Video/inputs/channels` | NVR'ning video-kirish **slotlari** — 16 kanalli NVR'da 6 ta kamera bo'lsa ham 16 ta element chiqishi mumkin | ⚠ **Ikkinchi darajali** — bo'sh slotni kamera deb yaratib qo'yish xavfi |
| `/ISAPI/Streaming/channels` | Har kanalning **kodek/rezolyutsiya/bitreyt** sozlamalari (`101`, `102`, `201`…) | ⚠ **Boyituvchi**, ro'yxat manbai emas — lekin `{ch}01`/`{ch}02` mavjudligini **tasdiqlaydi** |
| `/ISAPI/System/capabilities` | Qurilma imkoniyatlari sxemasi | ℹ Diagnostika uchun; kashfiyot uchun shart emas |

> **Nega `Streaming/channels` ro'yxat manbai emas:** Hikvision hujjatida DVR uchun "channel" mahalliy kirish oqimini, NVR uchun esa **masofaviy** media oqimini bildiradi [CITED: Hikvision ISAPI 2.0 RaCM Service guide]. Ya'ni NVR'da `Streaming/channels` allaqachon `InputProxy` orqali ro'yxatga olingan narsani **oqim nuqtayi nazaridan** ko'rsatadi. Uni birlamchi manba qilish "qaysi kamera qaysi kanalda" ma'lumotini (IP, model, nom) yo'qotardi.

#### 2-qadam-B — standalone IP-kamera bo'lsa

`<deviceType>` `IPCamera`/`IPDome` bo'lsa `InputProxy` **404 beradi** (u NVR/gibrid-DVR ga xos: *"NVRs and hybrid DVRs support external IP network devices as their input sources through this API"* [CITED: Hikvision IP Surveillance API (RaCM Part) User Guide]). Bunday qurilmada:

```
GET /ISAPI/System/Video/inputs/channels    # odatda 1 ta kanal
GET /ISAPI/Streaming/channels              # 101 / 102 (asosiy / sub)
```

va bitta kamera yozuvi yaratiladi (`channel_no = 1`).

> Karmana bozorida NVR kutilyapti, lekin **self-service qoidasi** boshqa bozor standalone kamera ulashini ta'qiqlamaydi. Ikki yo'l ham quriladi — farq ~30 qator kod, keyin retrofit qilish esa butun kashfiyot oqimini qayta ochishni talab qilardi.

#### Kashfiyot ketma-ketligi (yakuniy)

```
1. GET /ISAPI/System/deviceInfo            → model, seriya, deviceType, firmware
2. GET /ISAPI/Security/adminAccesses       → RTSP porti (A.2)
3. deviceType ∈ {NVR, DVR, HDVR}?
     HA  → GET /ISAPI/ContentMgmt/InputProxy/channels
           GET /ISAPI/ContentMgmt/InputProxy/channels/status
     YO'Q→ GET /ISAPI/System/Video/inputs/channels
4. Har kanal uchun: RTSP URL hosil qilish (A.2), yozuvni upsert qilish (A.4)
5. (ixtiyoriy, sozlanadigan) Har kanal uchun bitta ISAPI /picture tekshiruvi
```

**Ishonch:** endpoint yo'llari va `deviceInfo` XML'i — **HIGH** (real qurilmadan yozib olingan fixture). `InputProxy` javobining **aniq maydon nomlari** — **MEDIUM** (uch mustaqil manba mos keladi, lekin verbatim XML to'liq o'qilmadi → simulyator fixture'i **haqiqiy dump'dan** olinishi shart, B.7 ga qarang).

---

### A.2 — RTSP URL hosil qilish va portni kashf etish

#### Kanal raqamlash qoidasi

Hikvision RTSP yo'li **`{kanal}{oqim}`** shaklidagi ikki qismli raqamdan iborat [CITED: uchkunr/hikvision-best-practices; Hikvision USA support "How do I get my RTSP stream?"]:

```
rtsp://<host>:<rtsp_port>/Streaming/Channels/101    # kamera 1, ASOSIY oqim
rtsp://<host>:<rtsp_port>/Streaming/Channels/102    # kamera 1, SUB oqim
rtsp://<host>:<rtsp_port>/Streaming/Channels/1601   # kamera 16, asosiy
```

Ya'ni **`stream_id = channel_no * 100 + stream_index`**, bunda `stream_index`: `1` = asosiy (main), `2` = sub, `3` = uchinchi oqim (agar qurilma qo'llasa).

| Nuance | Tafsilot |
|--------|----------|
| **Katta-kichik harf** | Yo'lda `/Streaming/Channels/` (bosh harflar bilan) — ISAPI yo'lidagi `/ISAPI/Streaming/channels/` bilan **adashtirmang**. RTSP yo'li ISAPI yo'li **emas** |
| **Eski firmware** | Juda eski qurilmalarda `/h264/ch1/main/av_stream` ko'rinishi uchraydi. Bu **fallback shabloni** sifatida sozlamaga chiqariladi, lekin standart emas |
| **Parol URL ichida** | `rtsp://user:pass@host:554/...` ishlaydi, lekin **maxsus belgilar** (`@`, `:`, `/`, `#`) URL-encode qilinishi **shart** — aks holda parser hostni noto'g'ri ajratadi. Tavsiya: URL'da parol saqlanmasin (D.13) |
| **Sub-oqim mavjudligi** | Har kanalda `102` bo'lishi kafolatlanmagan. `GET /ISAPI/Streaming/channels/{ch}02` **404/400** bersa sub-oqim yo'q → kamera yozuvida `substream_url = NULL` |

#### RTSP portini **taxmin qilmang**

```
GET /ISAPI/Security/adminAccesses
```

`<AdminAccessProtocolList>` qaytaradi; har elementda `<id>`, `<protocol>` (`HTTP`/`HTTPS`/`RTSP`/`DEV_MANAGE`), `<portNo>` va `<enabled>` [CITED: Hikvision IP Surveillance API User Guide v2.6 + `hikvision_next` fixture ro'yxatida `Security/adminAccesses` mavjud]. Odatiy qiymatlar: HTTP 80, HTTPS 443, DEV_MANAGE 8000, **RTSP 554**.

**Nega bu muhim:** ko'p o'rnatuvchilar RTSP portini o'zgartiradi (masalan 10554) — ayniqsa bir nechta NVR bitta ommaviy IP ortida bo'lganda. 554 ni qotirib qo'yish **jimgina ishlamaydigan** kamera yozuvlari tug'diradi: kashfiyot yashil, kadr olish qora. Qoida:

```
rtsp_port = adminAccesses dagi RTSP portNo   (protocol=RTSP, enabled=true)
            → topilmasa: 554 (fallback, kamera yozuviga "taxmin qilingan" bayrog'i bilan)
```

Xuddi shu javobdan `HTTPS enabled=true` ekani ham olinadi — kelajakda ISAPI'ni TLS ustidan chaqirish uchun (o'z-o'zini imzolagan sertifikat → `verify=False` **faqat tunnel ichida**, C.11 ga qarang).

#### URL — saqlanadigan qiymat emas, **hosila**

Bazada `rtsp_url` **matn sifatida saqlanmaydi**. Saqlanadigani: `nvr.host`, `nvr.rtsp_port`, `camera.channel_no`. URL sof funksiyada hosil qilinadi:

```python
def rtsp_url(host: str, port: int, channel_no: int, *, substream: bool = False) -> str:
    """Hikvision RTSP yo'li: {kanal}{oqim} — 101 = kanal 1 asosiy, 102 = sub."""
    stream_id = channel_no * 100 + (2 if substream else 1)
    return f"rtsp://{host}:{port}/Streaming/Channels/{stream_id}"
```

Sabab: NVR IP'si yoki porti o'zgarganda **bitta qator** yangilanadi, 25 ta kamera URL'i emas. Va parol URL'ga **hech qachon** kirmaydi — u alohida, shifrlangan holda turadi va faqat go2rtc konfiguratsiyasi hosil qilinayotganda ochiladi (D.13).

---

### A.3 — Digest vs Basic, va SC#3 talab qilgan **aniq** xato taksonomiyasi

Bu bo'lim SC#3 ning to'g'ridan-to'g'ri javobi. **Markaziy muammo:** parol xato ham, soat farqi ham, qulflangan hisob ham, `digest`-only firmware ham — **hammasi `401` beradi**. Javob kodi yetarli emas.

#### Digest autentifikatsiyasi qanday ishlaydi (wire darajasida)

`httpx.DigestAuth` RFC 7616/2617 oqimini bajaradi [CITED: uchkunr/hikvision-best-practices]:

1. Klient **autentifikatsiyasiz** so'rov yuboradi → qurilma `401` + `WWW-Authenticate: Digest realm="...", nonce="...", qop="auth"` qaytaradi
2. Klient hisoblaydi: `HA1 = MD5(user:realm:pass)`, `HA2 = MD5(method:uri)`, `response = MD5(HA1:nonce:nc:cnonce:qop:HA2)`
3. Klient so'rovni `Authorization: Digest ...` bilan **qayta yuboradi**
4. `nc` (nonce count) har so'rovda oshiriladi; ulanish tirik saqlanadi

⚠ **Bu HAR ISAPI CHAQIRUVI UCHUN IKKI MARTA BORISH degani.** 25 kanal × 2 borish × tunnel kechikishi — E.16 dagi "kashfiyot inline emas, job" qarorining asosiy sababi. Yumshatish: **bitta `httpx.AsyncClient` ni butun kashfiyot davomida qayta ishlatish** (keep-alive + `httpx.DigestAuth` nonce'ni saqlaydi).

#### Xato → sabab → tuzatish jadvali (SC#3 kontrakti)

| Kuzatiladigan signal | Sabab (`error_code`) | Foydalanuvchiga ko'rsatiladigan tuzatish yo'li |
|---------------------|----------------------|-----------------------------------------------|
| `401` + javob tanasida `<lockStatus>locked</lockStatus>` va `<unlockTime>` | `nvr_account_locked` | "Hisob **N daqiqaga** qulflangan (ketma-ket xato urinishlar). Kuting yoki NVR'dan qulfni oching." **Qayta urinish TAQIQLANADI** — u qulf muddatini uzaytiradi |
| `401` **takrorlanadi**, `WWW-Authenticate` da `stale` yo'q, tana `lockStatus` bermaydi | `nvr_bad_credentials` | "Login yoki parol noto'g'ri." ⚠ **Ketma-ket ~5 urinishdan keyin hisob 30 daqiqaga qulflanadi** — shuning uchun avtomatik retry **YO'Q** |
| Qurilmaning `Date` sarlavhasi mahalliy UTC dan **>300 s** farq qiladi | `nvr_clock_drift` | "NVR soati **{N} daqiqa** farq qilyapti (qurilma: {device_time}, server: {server_time}). NVR sozlamalarida NTP'ni yoqing." — **`401` dan OLDIN aniqlanadi** |
| `401` + `WWW-Authenticate: ... stale=true` qayta-qayta | `nvr_digest_stale` | Nonce eskirgan/rad etilgan → deyarli har doim **soat farqi**. Yuqoridagi bilan bir xil tuzatish yo'li |
| `Authorization: Digest` bilan `401`, lekin **Basic bilan `200`** | `nvr_auth_mode_basic_only` | "Qurilmaning Web-autentifikatsiya rejimi `digest/basic` ga o'rnatilishi kerak." ⚠ Basic **faqat tunnel ichida** va **faqat diagnostika uchun** sinaladi (pastga qarang) |
| `403` yoki `<statusCode>` ≠ 1 bilan `Not Authorized` | `nvr_user_no_permission` | "Bu foydalanuvchida ISAPI/masofaviy kirish huquqi yo'q. NVR'da `Remote: Parameters Settings` va `Remote: Live View` huquqlarini bering." |
| `404` `/ISAPI/...` ga | `nvr_isapi_unavailable` | "Qurilma ISAPI'ni qo'llamaydi yoki manzil noto'g'ri (bu NVR'ning web-portimi?)" |
| TCP `ECONNREFUSED` / `ETIMEDOUT` | `nvr_unreachable` | "Manzilga yetib bo'lmadi. **WireGuard tunneli faolmi?** Manzil va port to'g'rimi?" — C.11 ga bog'lanadi |
| TLS protokol darajasidagi xato | `nvr_tls_untrusted` | Qo'l siqish (handshake) muvaffaqiyatsiz: mos keluvchi shifr to'plami yo'q, protokol versiyasi rad etildi, yoki javob TLS emas. **Muhim:** o'z-o'zini imzolagan sertifikat bu kodni ishga tushirmaydi — WireGuard tunneli ichida u **ataylab qabul qilinadi** (`verify=False`, `client.py`), chunki tunnel allaqachon transport ishonchini beradi. Ya'ni bu kod sertifikat *ishonchsizligi* uchun emas, TLS *ishlamasligi* uchun. |
| Kanal ro'yxatda bor, lekin `status` da `online=false` | `channel_offline` | "Kanal {N} ({nom}) oflayn — kamera o'chgan yoki kabel uzilgan." **Kamera yozuvi baribir yaratiladi**, `status='offline'` bilan (SC#2) |
| `Maximum number of streams` / oqim ochilmaydi | `nvr_stream_limit` | "NVR'ning bir vaqtdagi oqim/bitreyt chegarasiga yetildi. Sub-oqimga o'ting yoki boshqa klientlarni uzing." — A.5 |
| Digest muvaffaqiyatli, lekin `deviceType` Hikvision emas | `device_not_supported` | "Bu qurilma qo'llab-quvvatlanmaydi ({model}). MVP'da faqat Hikvision ISAPI" |

#### Soat farqini **401 dan oldin** aniqlash — eng qimmatli bitta hiyla

Har HTTP javobida `Date` sarlavhasi bo'ladi. Digest **muvaffaqiyatsiz bo'lganda ham** birinchi `401` javob `Date` ni olib keladi:

```python
# Birinchi (autentifikatsiyasiz) javobdan — 401 bo'lsa ham
device_time = parsedate_to_datetime(response.headers["Date"])   # email.utils
drift = abs((datetime.now(UTC) - device_time).total_seconds())
if drift > 300:                       # Hikvision Digest tolerantligi ~5 daqiqa
    raise NvrClockDrift(drift_seconds=drift, device_time=device_time)
```

Bu SC#3 ni "parol xato?" degan noaniq javobdan **aniq, harakatga chorlaydigan** xabarga aylantiradi. Manba: *"Digest authentication and event payloads are highly sensitive to clock drift — NTP synchronization required. Clock drift exceeding 5 minutes rejects authentication"* [CITED: uchkunr/hikvision-best-practices].

Ikkinchi (mustaqil) manba — `GET /ISAPI/System/time` — qurilmaning **o'z** vaqt sozlamasini va NTP holatini beradi; muvaffaqiyatli autentifikatsiyadan keyin diagnostika sifatida chaqiriladi va UI'da "NTP: o'chirilgan" ogohlantirishini beradi.

#### Hisob qulflanishi — retry siyosatini **teskarisiga aylantiradi**

*"Account lockout occurs after ~5 failed attempts (30-minute lock, response includes `<lockStatus>locked</lockStatus>` and `<unlockTime>`)"* [CITED: uchkunr/hikvision-best-practices].

Bu **muhim natija**: `tenacity` bilan "3 marta qayta urinish" — bu yerda **zararli**. Qoida:

| Xato sinfi | Retry |
|-----------|-------|
| Tarmoq (timeout, connection reset, 5xx) | ✅ `tenacity`, eksponensial, ≤3 urinish |
| `401` / autentifikatsiya | ❌ **HECH QACHON** — hisobni qulflaydi |
| `nvr_account_locked` | ❌ Retry yo'q + `unlockTime` gacha yangi urinish **bloklanadi** (ilova qatlamida) |

#### `httpx.DigestAuth` xususiyatlari

```python
auth = httpx.DigestAuth(username, password)
async with httpx.AsyncClient(auth=auth, timeout=httpx.Timeout(10.0, connect=5.0)) as client:
    ...
```

| Xususiyat | Tafsilot |
|-----------|----------|
| Ikki bosqichli | Har **yangi klient** uchun birinchi so'rov 401 oladi. Bitta klientni qayta ishlatish — 25 kanal uchun 25 ta ortiqcha borishni tejaydi |
| Timeout **majburiy** | `httpx` standarti 5 s; tunnel ortidagi NVR sekinroq. `connect=5, read=10` tavsiya etiladi. **`None` (cheksiz) HECH QACHON** — job osilib qoladi |
| `verify` | Tunnel ichidagi o'z-o'zini imzolagan sertifikat uchun `verify=False` **faqat HTTPS tanlanganda va faqat tunnel ichida**. Standart — `http://` tunnel ichida |
| Redirect | `follow_redirects=False` — ISAPI redirect qilmaydi; qilsa bu shubhali |
| Body qayta yuborish | Digest so'rovni takrorlaydi → `GET` uchun muammosiz. Bu fazada `PUT`/`POST` ISAPI chaqiruvlari yo'q |

**Ishonch:** Digest mexanikasi — **HIGH**. Qulflanish chegarasi (~5 urinish / 30 daq) va soat tolerantligi (5 daq) — **MEDIUM** (bitta ishonchli manba, firmware bo'yicha o'zgarishi mumkin) → `[ASSUMED]`, A1/A2 taxminlariga qarang.

---

### A.4 — Idempotent qayta skanerlash: qaysi kalit barqaror?

SC#2: *"yangi kanal qo'shiladi, yo'qolgani `offline` deb belgilanadi, mavjudi tegilmaydi — takroriy kamera yozuvi yaratilmaydi."*

#### Nomzod kalitlar va ularning taqdiri

| Nomzod | Barqarormi | Verdikt |
|--------|-----------|---------|
| **`(nvr_id, channel_no)`** | NVR'ning o'zi shu bilan adreslaydi; kanal raqami slotga bog'langan | ✅ **TANLANDI** |
| Kamera seriya raqami | Eng "to'g'ri" ko'rinadi, LEKIN `InputProxy` javobida **kafolatlanmagan**; olish uchun har kamera IP'siga alohida so'rov kerak (tunnel ortida 25 ta qo'shimcha borish) | ❌ Kalit sifatida rad etildi |
| Kamera MAC'i | Xuddi shu muammo + NVR ko'pincha uni ko'rsatmaydi | ❌ |
| Kamera IP'si (`sourceInputPortDescriptor/ipAddress`) | DHCP bilan **o'zgaradi** | ❌ Kalit emas, **atribut** |
| Kanal nomi (`<name>`) | Admin NVR'da istagancha o'zgartiradi | ❌ Kalit emas, **atribut** |

**Nega `channel_no` g'alaba qozonadi:** RTSP URL **aynan kanal raqamidan** hosil bo'ladi (A.2). Boshqa kalit tanlansa, identifikator bilan manzil **ajralib ketardi** — kanal 3 dagi kamera kanal 7 ga ko'chirilganda yozuv "o'sha kamera" bo'lib qolardi, lekin URL noto'g'ri bo'lardi. Kanal raqami — bu **uyachaning** identifikatori, va biz aynan uyachani suratga olamiz.

#### Fizik almashtirishni yo'qotmaslik

Kanal raqamini kalit qilish "kanal 3 dagi kamera almashtirildi" faktini yo'qotish xavfini tug'diradi. Yechim — kalit emas, **kuzatuv**:

```
cameras:
  PK/UNIQUE : (market_id, nvr_id, channel_no)      ← identifikatsiya
  atributlar: source_ip, source_port, source_model ← kuzatiladi
```

Qayta skanerlashda `source_ip` yoki `source_model` o'zgargan bo'lsa — yozuv **yangilanadi** va **audit qatori** yoziladi (`camera_source_changed`, `old→new`). 5-fazada bu muhim bo'ladi: kamera almashtirilsa **zona poligonlari yaroqsiz** bo'lishi mumkin, va bu signal aynan shu yerdan keladi.

#### Upsert semantikasi (SC#2 ning uch qoidasi)

```sql
-- 1) YANGI yoki MAVJUD kanal
INSERT INTO cameras (market_id, nvr_id, channel_no, name, source_ip, source_model,
                     status, first_seen_at, last_seen_at)
VALUES (:market_id, :nvr_id, :channel_no, :name, :ip, :model,
        :status, now(), now())
ON CONFLICT (market_id, nvr_id, channel_no) DO UPDATE
SET last_seen_at  = now(),
    status        = EXCLUDED.status,
    source_ip     = EXCLUDED.source_ip,
    source_model  = EXCLUDED.source_model,
    -- ⚠ `name` FAQAT admin uni QO'LDA o'zgartirmagan bo'lsa yangilanadi
    name          = CASE WHEN cameras.name_overridden THEN cameras.name
                         ELSE EXCLUDED.name END;

-- 2) SHU SKANDA KO'RINMAGAN kanallar → offline (o'chirilmaydi)
UPDATE cameras
SET status = 'offline', last_seen_at = last_seen_at
WHERE nvr_id = :nvr_id AND last_seen_at < :run_started_at;
```

**Uchta qat'iy qoida:**

| Qoida | Nima uchun |
|-------|-----------|
| **Kamera yozuvi HECH QACHON o'chirilmaydi** | 4–7 fazalarda snapshot, zona, dalil-rasm unga bog'lanadi. `DELETE` tarixiy dalilni yo'q qilardi. Yo'qolgan kanal = `status='offline'` |
| **`name_overridden` bayrog'i majburiy** | Admin kamerani "Sabzavot qatori" deb nomlaganda keyingi skan uni NVR'dagi "Camera 03" ga **qaytarib qo'ymasligi** kerak. SC#2 ning "mavjudi tegilmaydi" qismi aynan shu |
| **`first_seen_at` hech qachon yangilanmaydi** | Audit va diagnostika uchun |

#### Kashfiyot yugurishlarining tarixi

Har skan `nvr_discovery_runs` ga qator yozadi: `started_at`, `finished_at`, `status`, `channels_found`, `channels_added`, `channels_marked_offline`, `error_code`, `error_detail`. Bu SC#2 ni **kuzatiladigan** qiladi ("ikkinchi skan 0 ta qo'shdi") va SC#3 ning xatolarini tarixga yozadi.

---

### A.5 — Bir vaqtdagi sessiya limiti: ulanish soni emas, **bitreyt**

CLAUDE.md bu risk bo'yicha "odatda 6–16" deb yozgan. Tadqiqot bu raqamni **aniqlashtirdi va manzarani o'zgartirdi**.

#### Haqiqiy chegara qaerda

| Chegara turi | Qiymat | Manba |
|-------------|--------|-------|
| Umumiy "remote connections" | **128** (model bo'yicha o'zgaradi) | [CITED: supportusa.hikvision.com — "maximum number of streams"] |
| **Chiquvchi bitreyt (outgoing bandwidth)** | **Amaldagi to'siq** — modelga qarab ~32–256 Mbps | [ASSUMED — model spetsifikatsiyalari asosida] |
| Bir vaqtda ko'rish (Hik-Connect ilovasi) | 16 kamera | [CITED: supportusa.hikvision.com] |

Hikvision hujjati aniq ogohlantiradi: *"Remote connections and bandwidth are not the same concept"* va *"what constitutes the 128 concurrent connections is not clearly defined"* [CITED: supportusa.hikvision.com]. Amalda **bitreyt birinchi tugaydi**:

```
25 kanal × asosiy oqim (4 MP H.265 ≈ 4 Mbps)  = 100 Mbps  ← ko'pchilik NVR'da IMKONSIZ
25 kanal × sub-oqim   (D1  H.264 ≈ 0.5 Mbps)  = 12.5 Mbps ← qulay
```

#### Buning arxitekturaviy oqibati (bu faza qarori)

| Qaror | Sabab |
|-------|-------|
| **go2rtc doimiy ravishda faqat SUB-oqimga ulanadi** | 25 kanal sub-oqimda ~12 Mbps — NVR ham, bozor DSL'i ham ko'taradi |
| **Asosiy oqim faqat talab bo'yicha, bittalab** | Direktor "sifatli ko'rish" bosganda bitta kanal uchun asosiy oqim ochiladi va yopilganda uziladi |
| **go2rtc oqimni faqat tomoshabin bo'lganda ochadi** | go2rtc standart xulqi shunday (lazy) — bu **afzallik**, uni o'chirmang |
| **Kadr olish (4-faza) go2rtc'ning ochiq sub-oqimidan `/api/frame.jpeg` bilan** | Yangi RTSP sessiyasi ochilmaydi (CLAUDE.md tanlovi bilan mos) |
| **Zaxira: ISAPI `/picture`** — RTSP sessiyasini **umuman** ishlatmaydi | Sessiya byudjeti bo'yicha eng arzon yo'l; sekin, lekin oqim ochmaydi |
| **Kashfiyot va ulanish testi oqim OCHMAYDI** | Faqat ISAPI HTTP so'rovlari. RTSP tekshiruvi alohida, **ixtiyoriy va bittalab** qadam |

#### Chegara qanday namoyon bo'ladi

Aynan bu joyda **eng ko'p noaniqlik bor** — va bu SC#3 uchun muhim:

- go2rtc `RTSP: 453 Not Enough Bandwidth` yoki `503 Service Unavailable` ni ko'rishi mumkin
- Ba'zi firmware **jimgina** ulanishni uzadi (RTSP `TEARDOWN` yoki TCP FIN) — xato kodi **umuman yo'q**
- Web-UI'da "Maximum number of streams" ko'rinadi, lekin bu **RTSP javobiga tarjima qilinmasligi mumkin**

Shuning uchun **`nvr_stream_limit` ni faqat kodga qarab aniqlab bo'lmaydi**. Amaliy heuristika (simulyatorda modellashtiriladi, B.8):

```
Agar bitta kanal ulansa, lekin N-chi kanal (N > 1) ketma-ket uzilsa
va NVR ISAPI'ga hamon javob bersa → nvr_stream_limit deb taxmin qilinadi
```

⚠ Bu **heuristika, kafolat emas** — `error_detail` da xom RTSP javobi saqlanadi va xabar "ehtimol" tarzida beriladi. Real qurilmada aniqlanadi (Open Question OQ-2).

**Ishonch:** 128 raqami — **MEDIUM** (rasmiy support maqolasi, lekin model bo'yicha o'zgaradi). "Bitreyt birinchi tugaydi" — **MEDIUM** (mulohaza + Hikvision'ning o'z ogohlantirishi). Chegaraning **RTSP javobida qanday ko'rinishi** — **LOW** → simulyatorda ikkala variant ham modellashtiriladi.

---

## B. Simulyator (CAM-09)

> Bu bo'lim fazaning **eng katta noma'lumi**. CAM-09 simulyatorni birinchi darajali yetkazib berish mahsuloti qiladi, ya'ni u "test yordamchisi" emas — usiz SC#7 bajarilmaydi va faza yopilmaydi.

### B.6 — Nima mavjud va nima tanlanadi

#### Ekotizim tekshiruvi: **tayyor Hikvision NVR emulyatori YO'Q**

Ikkita mustaqil qidiruv (GitHub topics `hikvision`, `isapi`, `hikvision-isapi`, `hikvision-camera` + maqsadli "mock/simulator/emulator" qidiruvi) **faqat klientlarni** topdi:

| Topilgan | Nima | Bizga yaroqlimi |
|----------|------|------------------|
| `jackblk/hikvision-isapi-py` | ISAPI **klienti** (Python) | ❌ Klient, server emas |
| `evercam/hikvision_client` | ISAPI **klienti** (Elixir) | ❌ |
| `Tedyst/HikLoad` | Video yuklab oluvchi **klient** | ❌ |
| `maciej-or/hikvision_next` | Home Assistant integratsiyasi (**klient**) | ⚠ **Server emas, LEKIN `tests/fixtures/devices/*.json` — real qurilmalardan yozib olingan javoblar.** Bu bizning oltinimiz (pastga qarang) |
| `uchkunr/hikvision-best-practices` | Hujjat/qo'llanma | ⚠ Xulq spetsifikatsiyasi manbai |
| ONVIF emulyatorlari (`onvif-srvd` va h.k.) | ONVIF SOAP simulyatsiyasi | ❌ **Noto'g'ri protokol.** CLAUDE.md ONVIF'ni snapshot uchun allaqachon rad etgan; kashfiyot ISAPI orqali boradi |

**Xulosa:** simulyator **qo'lda quriladi**. Bu yomon xabar emas — mockning butun qiymati aynan **xato yo'llarini** ishonchli qayta tug'dirishida (noto'g'ri parol, soat farqi, offline kanal, sessiya limiti), va bu tayyor emulyatorda baribir bo'lmasdi. [VERIFIED: 2026-08-02 qidiruvi — negative claim, ikki mustaqil qidiruv bilan]

#### Nomzod arxitekturalar

| Variant | Digest auth | Holatli (lockout, drift) | Compose profili | E2E (SC#7) | Verdikt |
|---------|-------------|--------------------------|-----------------|-----------|---------|
| **FastAPI ISAPI-mock** (`services/nvr-sim/`) | ✅ RFC 7616 qo'lda (~70 qator) | ✅ To'liq | ✅ | ✅ | ✅ **TANLANDI** |
| WireMock / Mockoon (statik XML) | ⚠ Digest challenge'ni to'g'ri qila olmaydi | ❌ | ✅ | ⚠ | ❌ Rad etildi |
| `respx` / `pytest-httpx` (transport mock) | ❌ Handshake umuman bo'lmaydi | qisman | ❌ | ❌ | ⚠ **Parallel ishlatiladi** — parser **unit** testlari uchun to'g'ri vosita, lekin CAM-09 ni bajarmaydi |
| Nginx + statik fayl | ❌ | ❌ | ✅ | ❌ | ❌ |
| Real qurilmani kutish | — | — | — | — | ❌ **ROADMAP taqiqlaydi** |

**Nega FastAPI:** `core-api` allaqachon FastAPI 0.140.13 ustida; sim uchun yangi til, yangi build zanjiri va yangi ko'nikma kerak emas. Konteyner `core-api` Dockerfile'ining `dev` target'ini qayta ishlatadi → CI'da **qo'shimcha build vaqti ~0**.

**Nega `respx` yetarli emas:** u `httpx` transportini almashtiradi, ya'ni **Digest handshake umuman bajarilmaydi**. Aynan handshake bizning eng nozik joyimiz (A.3). `respx` bilan qurilgan test "kod XML'ni to'g'ri parse qiladi" ni isbotlaydi, "kod NVR bilan gaplasha oladi" ni **emas**. Ikkalasi ham kerak, lekin ular **boshqa qatlamlar**:

```
tests/unit/test_isapi_parser.py        → respx / xom XML satrlari (tez, hermetik)
tests/integration/test_nvr_discovery.py → JONLI nvr-sim konteyneri (SC#7 darvozasi)
```

#### RTSP manbai: go2rtc'ning O'ZI (yangi bog'liqlik yo'q)

CAM-09 "ISAPI mock + **go2rtc RTSP manbai**" deydi va bu to'g'ri tanlov: go2rtc allaqachon stekda va u **to'liq RTSP serveri** (standart port **8554/tcp**) [CITED: go2rtc README — `rtsp: listen: ":8554"`].

Faylni tsiklda uzatishning **hujjatlashtirilgan va ishonchli** yo'li — `exec:` manbai `{output}` o'rin egallovchisi bilan:

```yaml
# ops/go2rtc/go2rtc.sim.yaml
streams:
  sim_cam_01: >-
    exec:ffmpeg -re -stream_loop -1 -i /media/bazaar.mp4
    -c:v libx264 -preset ultrafast -tune zerolatency -g 25 -an -f rtsp {output}
  sim_cam_02: ...
```

`{output}` mexanikasi (hujjatlashtirilgan): go2rtc URL'ning MD5'idan noyob RTSP yo'lini hosil qiladi, `{output}` ni `rtsp://127.0.0.1:<rtsp.Port>/<md5>` bilan almashtiradi, buyruqni ishga tushiradi va `starttimeout` (standart **30 s**) davomida jarayonning RTSP `ANNOUNCE` bilan qaytib ulanishini kutadi [CITED: deepwiki AlexxIT/go2rtc — "FFmpeg and Exec Sources"].

| Detal | Qiymat / sabab |
|-------|----------------|
| `-re` | Real vaqt tezligida — **majburiy**, aks holda ffmpeg faylni bir zumda "o'ynab" tugatadi |
| `-stream_loop -1` | Cheksiz tsikl |
| `-g 25` | Har 25 kadrda keyframe → `/api/frame.jpeg` va WebRTC tez boshlanadi |
| `-an` | Audio yo'q — bozor kamerasida audio ishlatilmaydi, byudjetni tejaydi |
| `-preset ultrafast` | CI'da CPU byudjeti; sifat muhim emas |

> ⚠ `ffmpeg:/media/file.mp4#input=...` varianti ham bor, lekin `#input=` shabloni **hujjatda tsikl uchun ko'rsatilmagan** ([CITED: go2rtc.org/internal/ffmpeg/ — "The documentation does not mention looping"]). `exec:` yo'li aniq hujjatlashtirilgan → **`exec:` tanlanadi**.

#### Video manbai: CI uchun **sintetik**, dev uchun ixtiyoriy real fayl

| Muhit | Manba | Sabab |
|-------|-------|-------|
| **CI (standart)** | `ffmpeg -f lavfi -i testsrc2=size=1280x720:rate=12` + `drawtext` (kanal raqami va soat) | **Git'ga binar fayl qo'shilmaydi**, deterministik, ~0 disk. Kadr kelganini isbotlash uchun yetarli |
| **Dev (ixtiyoriy)** | `ops/sim/media/bazaar.mp4` (gitignore'da, `SIM_MEDIA_PATH` bilan) | Vizual tekshiruv va 5-fazaga tayyorgarlik |
| **5-faza (keyinroq)** | Karmanadan real kadrlar | Bu fazada **kerak emas** |

`drawtext` bilan kadrga kanal raqami va vaqt yozish **diagnostik jihatdan qimmatli**: "kanal 7 ni so'radim, kadrda 3 yozilgan" xatosi darhol ko'rinadi — bu aynan `{ch}01` raqamlash xatosining alomati.

---

### B.7 — Minimal ISAPI yuzasi: nima **haqiqatan** bajarilishi kerak

Qoida: **kashfiyot kodi sim'ni haqiqiy qurilmadan ajrata olmasligi kerak.** Har bir endpoint uchun "fidelity" ustuni nimani jiddiy qilish kerakligini aytadi.

| # | Endpoint | Metod | Fidelity darajasi | Nima bo'lishi SHART |
|---|----------|-------|-------------------|---------------------|
| 1 | **Digest challenge (barcha `/ISAPI/*` yo'llari)** | — | **TO'LIQ (RFC 7616)** | Autentifikatsiyasiz so'rovga `401` + `WWW-Authenticate: Digest realm=, nonce=, qop="auth", opaque=`. `response` ni **haqiqatan hisoblab tekshirish** (`MD5(HA1:nonce:nc:cnonce:qop:HA2)`). ⚠ Bu **stub bo'lmasligi kerak** — `httpx.DigestAuth` haqiqiy handshake'dan o'tishi kerak, aks holda A.3 dagi hech nima sinalmaydi |
| 2 | **`Date` sarlavhasi** | — | **TO'LIQ** | Har javobda RFC 7231 `Date`. **Sozlanadigan siljish** bilan — A.3 dagi soat-farqi aniqlashning yagona sinov yo'li |
| 3 | `/ISAPI/System/deviceInfo` | GET | **TO'LIQ (yozib olingan XML)** | `DS-7616NI-K2` fixture'idan **verbatim**, namespace bilan. `deviceType=NVR` |
| 4 | `/ISAPI/ContentMgmt/InputProxy/channels` | GET | **TO'LIQ (yozib olingan XML)** | `<InputProxyChannelList>` + N ta `<InputProxyChannel>` (`id`, `name`, `sourceInputPortDescriptor`). **Kanal soni sozlanadigan** (2 / 6 / 25) |
| 5 | `/ISAPI/ContentMgmt/InputProxy/channels/status` | GET | **TO'LIQ** | Har kanal uchun `<online>`; **istalgan kanalni oflayn qilish mumkin** |
| 6 | `/ISAPI/Security/adminAccesses` | GET | **TO'LIQ** | `AdminAccessProtocolList`: HTTP/HTTPS/RTSP/DEV_MANAGE + `portNo`. **RTSP porti sozlanadigan** (554 emas → 10554) — A.2 ni sinash uchun |
| 7 | `/ISAPI/System/Video/inputs/channels` | GET | **O'RTA** | Standalone-kamera yo'lini va "bo'sh slot" farqini sinash uchun |
| 8 | `/ISAPI/Streaming/channels/{id}` | GET | **O'RTA** | Mavjud kanal → kodek/rezolyutsiya XML'i; mavjud bo'lmagan sub-oqim → **404** (A.2 dagi `substream_url = NULL` yo'li) |
| 9 | `/ISAPI/Streaming/channels/{id}/picture` | GET | **O'RTA** | Haqiqiy JPEG bayt (go2rtc'dan yoki oldindan tayyorlangan). 4-faza zaxira yo'lining ilgagi |
| 10 | `/ISAPI/System/time` | GET | **PAST** | NTP holati diagnostikasi |
| 11 | `/ISAPI/System/capabilities` | GET | **PAST** | Statik XML; hozircha ishlatilmaydi |
| 12 | **Noma'lum `/ISAPI/*`** | any | **O'RTA** | `404` + Hikvision-uslub XML xato tanasi — "endpoint yo'q" yo'lini sinash |

#### Fixture'lar **haqiqiy dump'dan** keladi — bu majburiy

> ⚠ **`simulator-confirms-itself` ANTI-NAQSHI.** Agar sim XML'i bizning parserimiz kutgan shaklda qo'lda yozilsa, test faqat **"kod o'z taxminiga mos"** ekanini isbotlaydi. Bu yashil CI beradi va real qurilmada yiqiladi.

**Qoida:** `services/nvr-sim/fixtures/*.xml` fayllari `maciej-or/hikvision_next` repozitoriyasining `tests/fixtures/devices/DS-7616NI-K2.json` va `DS-7732NI-M4.json` (32 kanalli NVR — 25 kanalli Karmanaga eng yaqin) dump'laridan **ajratib olinadi**, qo'lda yozilmaydi. Fayl boshida manba, sana va qurilma modeli izohda qayd etiladi.

**Darvoza:** `tests/unit/test_sim_fixtures.py` — har fixture XML sifatida parse bo'lishi, Hikvision namespace'iga ega bo'lishi va manba izohiga ega bo'lishi tekshiriladi. Bu "kimdir XML'ni parserga moslab tuzatib qo'ydi" holatini ko'rinadigan qiladi.

---

### B.8 — Xato rejimlarini qayta tug'dirish (SC#3 ning yagona sinov yo'li)

Sim'ning **asosiy qiymati** shu yerda. Boshqarish uchun **ISAPI namespace'idan tashqarida** turgan control-plane:

```
POST /__sim__/state      {"mode": "...", ...}    # holatni o'rnatish
GET  /__sim__/state                              # joriy holat
POST /__sim__/reset                              # standart holatga
```

`/__sim__/` prefiksi ataylab: u **hech qachon** `/ISAPI/*` bilan chalkashmaydi, va prodda bunday yo'l umuman mavjud emas (sim konteyneri prodda ishlamaydi).

| Xato rejimi (`mode`) | Sim nima qiladi | Qaysi `error_code` ni sinaydi | SC |
|----------------------|-----------------|-------------------------------|-----|
| `ok` (standart) | Normal ishlaydi | — | SC#1 |
| `bad_password` | Digest `response` mos kelmasa `401` + yangi challenge | `nvr_bad_credentials` | SC#3 |
| `account_locked` | `401` + tana: `<userCheck><lockStatus>locked</lockStatus><unlockTime>1800</unlockTime></userCheck>` | `nvr_account_locked` + **retry bajarilmasligi** | SC#3 |
| `clock_drift` (`drift_seconds`) | `Date` sarlavhasini N soniyaga siljitadi (masalan `+420`) | `nvr_clock_drift` — **`401` dan oldin** | SC#3 |
| `digest_stale` | `401` + `WWW-Authenticate: ... stale=true` | `nvr_digest_stale` | SC#3 |
| `basic_only` | `Digest` ni rad etadi, `Basic` ni qabul qiladi | `nvr_auth_mode_basic_only` (`digest/basic` firmware) | SC#3 |
| `no_permission` | `403` + `<statusCode>6</statusCode><subStatusCode>notSupport</subStatusCode>` | `nvr_user_no_permission` | SC#3 |
| `channel_offline` (`channels: [3,7]`) | `status` javobida o'sha kanallar `<online>false</online>` | `channel_offline` + **kamera baribir yaratiladi** | SC#2, SC#3 |
| `channel_removed` (`channels: [5]`) | Kanalni ro'yxatdan **butunlay olib tashlaydi** | Kamera `offline` bo'ladi, **O'CHIRILMAYDI** | SC#2 |
| `channel_added` (`count: 8`) | Ro'yxatga yangi kanal qo'shadi | Yangi kamera qo'shiladi, mavjudlari **tegilmaydi** | SC#2 |
| `camera_swapped` (`channel: 3, ip: ...`) | Kanal 3 ning `ipAddress`/model'ini o'zgartiradi | `camera_source_changed` audit yozuvi (A.4) | SC#2 |
| `stream_limit` (`max: 4`) | 5-chi RTSP ulanishini rad etadi **VA** ISAPI'ga javob berishda davom etadi | `nvr_stream_limit` heuristikasi (A.5) | SC#3 |
| `slow` (`delay_ms: 8000`) | Har javobni kechiktiradi | Timeout xulqi va `arq` job byudjeti | SC#1 |
| `isapi_404` | Barcha `/ISAPI/*` ga `404` | `nvr_isapi_unavailable` | SC#3 |
| `unreachable` | Konteyner to'xtatiladi (`docker compose stop nvr-sim`) | `nvr_unreachable` | SC#3, SC#5 |
| `not_hikvision` | `deviceInfo` da boshqa `manufacturer` | `device_not_supported` | SC#3 |
| `port_moved` (`rtsp_port: 10554`) | `adminAccesses` boshqa portni beradi | RTSP porti **kashf etiladi**, taxmin qilinmaydi (A.2) | SC#1 |

**Muhim loyihalash qarori:** har rejim **bitta** integratsiya testiga to'g'ri keladi va test **`error_code` ni ham, foydalanuvchiga ko'rinadigan tuzatish matnini ham** tekshiradi. SC#3 "quruq xabar qabul qilinmaydi" deydi — bu darvoza aynan shu yerda.

`stream_limit` uchun `max: 4` ataylab kichik: 25 ta sim-kamera ko'tarish CI mashinasi uchun og'ir, chegara mantiqini esa 4 ta bilan ham to'liq sinash mumkin.

---

### B.9 — Compose topologiyasi, CI va prodga sizib ketmaslik

#### Compose profili

```yaml
# compose.yaml — mavjud profillar ustiga
#   (yo'q)  -> db, cache, core-api
#   migrate -> Alembic
#   web     -> frontend
#   proxy   -> nginx
#   test    -> pytest
#   sim     -> nvr-sim + go2rtc-sim      <-- YANGI

  nvr-sim:
    profiles: ["sim"]                       # <-- PRODGA SIZIB KETMAYDI
    build:
      context: .
      dockerfile: services/core-api/Dockerfile   # dev target qayta ishlatiladi
      target: dev
    command: ["uvicorn", "sim.main:app", "--host", "0.0.0.0", "--port", "8080"]
    working_dir: /app/services/nvr-sim
    environment:
      SIM_CHANNEL_COUNT: "${SIM_CHANNEL_COUNT:-6}"
      SIM_RTSP_HOST: go2rtc-sim
      SIM_RTSP_PORT: "8554"
      SIM_USERNAME: admin
      SIM_PASSWORD: "${SIM_PASSWORD:-Sim12345}"
      TZ: Asia/Tashkent
    volumes:
      - .:/app
    healthcheck:
      test: ["CMD", "python", "-c",
             "import urllib.request;urllib.request.urlopen('http://localhost:8080/__sim__/state')"]
      interval: 5s
      timeout: 3s
      retries: 10

  go2rtc-sim:
    profiles: ["sim"]
    image: alexxit/go2rtc:1.9.14
    volumes:
      - ./ops/go2rtc/go2rtc.sim.yaml:/config/go2rtc.yaml:ro
    # Xost portiga publish QILINMAYDI (T-01-04 naqshi) — faqat compose tarmog'i ichida
```

| Qaror | Sabab |
|-------|-------|
| **`profiles: ["sim"]`** | `docker compose up` (profilsiz) sim'ni **ishga tushirmaydi**. Prod deploy profilsiz — sizib ketish strukturaviy jihatdan imkonsiz |
| **`core-api` Dockerfile `dev` target'i** | Yangi Dockerfile yo'q, CI'da yangi build qatlami yo'q. `nvr-sim` faqat FastAPI + stdlib `hashlib` ishlatadi — **yangi paket qo'shilmaydi** |
| **Xost portiga publish yo'q** | Sim faqat compose tarmog'idan ko'rinadi |
| **Alohida go2rtc konteyneri** | Prod go2rtc va sim go2rtc **aralashmaydi** — sim NVR "tashqi qurilma" bo'lib qolishi kerak |

#### Testlar sim'ga qanday yo'naltiriladi

```yaml
  tests:
    profiles: ["test"]
    environment:
      NVR_SIM_BASE_URL: "http://nvr-sim:8080"     # <-- YANGI
```

Testda:

```python
@pytest.fixture
def sim_url() -> str:
    url = os.environ.get("NVR_SIM_BASE_URL")
    if not url:
        pytest.skip("nvr-sim ishlamayapti — `--profile sim` bilan ishga tushiring")
    return url
```

⚠ **`pytest.skip` — o'ylab qilingan xavf.** U testni jimgina o'tkazib yuborishi mumkin. Shuning uchun **CI'da skip TAQIQLANADI**: `tests/integration/test_nvr_discovery.py` da bitta `test_sim_is_reachable` bo'ladi va u CI'da `skip` emas, **`fail`** beradi (`CI=true` bo'lganda). Aks holda SC#7 "CI'da o'lchanadi" da'vosi jimgina yolg'onga aylanardi.

#### CI zanjiri

```bash
docker compose --profile sim --profile test up -d db cache nvr-sim go2rtc-sim
docker compose --profile test run --rm tests pytest tests/integration/test_nvr_discovery.py -x
```

`package.json` ga yangi yorliq (xost `make` ishlatmaydi — CLAUDE.md):

```json
"test:sim": "docker compose --profile sim up -d nvr-sim go2rtc-sim && docker compose --profile test run --rm tests pytest tests/integration -m sim -x"
```

`-m sim` markeri — `pyproject.toml` dagi `markers` ro'yxatiga qo'shiladi (2-fazada `tenancy` markeri uchun bir xil naqsh ishlatilgan).

#### Real qurilmaga o'tish — **sozlama**, kod emas

CAM-09 ning yakuniy da'vosi. Buni tekshiriladigan qiladigan narsa:

| Nima | Sim rejimi | Real rejim |
|------|-----------|-----------|
| NVR manzili | `nvr-sim:8080` (bazadagi `nvr_devices` qatori) | `10.10.0.5:80` |
| Login/parol | `admin` / `Sim12345` (bazada, Fernet bilan) | Real rekvizit |
| RTSP hosti | `adminAccesses` javobidan | `adminAccesses` javobidan |
| **Kod farqi** | **YO'Q** | **YO'Q** |

**Darvoza:** `tests/unit/test_no_sim_branching.py` — `services/core-api/app/` ichida `nvr-sim`, `__sim__`, `SIM_` satrlari **umuman uchramasligi** tekshiriladi. Bu "sim uchun maxsus tarmoqlanish" ni kodga sizib kirishidan strukturaviy himoya. Ilova uchun sim — bu shunchaki **bazadagi bir qator**.

---

## C. Xavfsizlik va tarmoq

### C.10 — NVR rekvizitlarining Fernet shifri (SC#4)

#### 1-fazadan meros: nima allaqachon bor

| Aktiv | Holat | Manba |
|-------|-------|-------|
| `cryptography==49.0.0` | ✅ **Allaqachon `services/core-api/pyproject.toml` da** — yangi paket kerak emas | `pyproject.toml:17` |
| `rtsp_password`, `nvr_password` log filtrida | ✅ **Allaqachon `SENSITIVE_KEYS` da** (izohda "spec §5 — RTSP parollari shifrlangan saqlanadi" deb qayd etilgan) | `packages/sbozor-core/sbozor_core/logging.py:59-61` |
| `censor_secrets` **rekursiv** protsessori | ✅ Ichma-ich lug'at/ro'yxatlarni ham maskalaydi | `logging.py:72-113` |
| `audit_repo.mask_sensitive` | ✅ Audit JSONB uchun bir xil chuqurlikdagi juftlik | `logging.py` docstring |
| Fernet kaliti / shifrlash moduli | ❌ **YO'Q — bu faza quradi** | — |
| `Settings` da shifr kaliti maydoni | ❌ **YO'Q** | `settings.py` |

> ✅ **Kutilmagan yaxshi xabar:** 1-faza log filtrini **NVR parollarini oldindan hisobga olib** yozgan. Ya'ni SC#4 ning "jurnalda ko'rinmaydi" qismi **allaqachon qamrab olingan** — shart shuki, parol `nvr_password` / `rtsp_password` **nomlangan kalit** sifatida uzatilsin, `event` matni ichiga qo'shilmasin (bu qoida `logging.py` docstring'ida aniq yozilgan).

#### Kalit manbai va shakli

```python
# app/settings.py ga qo'shiladi
nvr_credential_key: str          # base64 urlsafe 32 bayt — Fernet formati
```

| Qoida | Sabab |
|-------|-------|
| Kalit **faqat muhitdan** (`NVR_CREDENTIAL_KEY`), `.env` gitignore'da, `.env.example` da faqat nom | 12-faktor; `settings.py` docstring'idagi mavjud qoida |
| Kalit **hech qachon bazada emas** | SC#4: "bazaga kirgan odam ham ochiq matn parol ko'rmaydi". Kalit DB'da bo'lsa shifr ma'nosiz |
| Kalit `JWT_SECRET` dan **ALOHIDA** | Ikki xil xavf modeli. JWT kaliti almashtirilsa sessiyalar tushadi (arzon); shifr kaliti almashtirilsa **ma'lumot yo'qoladi** (qimmat) |
| `field_validator` bilan format tekshiruvi startup'da | `JWT_SECRET` uchun mavjud naqsh (`_validate_jwt_secret`). Noto'g'ri kalit **ishga tushishda** yiqilsin, birinchi kamera qo'shilganda emas |

```python
@field_validator("nvr_credential_key")
@classmethod
def _validate_nvr_key(cls, value: str) -> str:
    try:
        Fernet(value.encode())          # format + uzunlikni tekshiradi
    except (ValueError, TypeError) as exc:
        raise ValueError(
            "NVR_CREDENTIAL_KEY — Fernet kaliti bo'lishi kerak. "
            'Hosil qilish: python -c "from cryptography.fernet import Fernet;'
            'print(Fernet.generate_key().decode())"'
        ) from exc
    return value
```

#### Rotatsiya: `MultiFernet` **birinchi kundan**

Bu **kelajak uchun optimizatsiya emas** — u keyin retrofit qilinganda mavjud shifrlangan qatorlar o'qib bo'lmas holga keladi.

```python
# app/security/secrets.py (YANGI)
def build_cipher(primary: str, retired: Sequence[str] = ()) -> MultiFernet:
    """Birinchi kalit YOZADI, hammasi O'QIYDI (kalit rotatsiyasi)."""
    return MultiFernet([Fernet(k.encode()) for k in (primary, *retired)])
```

Muhit: `NVR_CREDENTIAL_KEY` (joriy) + `NVR_CREDENTIAL_KEYS_RETIRED` (vergul bilan, ixtiyoriy). Rotatsiya: yangi kalitni birinchi qilib qo'ying, eskisini `RETIRED` ga ko'chiring, `MultiFernet.rotate()` bilan qatorlarni qayta shifrlang. **`cryptography` bu API'ni o'zi beradi — hand-roll qilinmaydi.**

#### Parol **hech qachon** javobda ko'rinmaydi — strukturaviy usul

```python
class NvrDeviceRead(BaseModel):
    id: UUID
    host: str
    port: int
    username: str
    model: str | None
    # parol maydoni UMUMAN YO'Q — `exclude=True` emas, MAVJUD EMAS
    has_password: bool          # UI "parol o'rnatilgan" deb ko'rsatadi
```

| Yondashuv | Nega rad etildi / tanlandi |
|-----------|---------------------------|
| `password: str = Field(exclude=True)` | ❌ `model_dump()` chaqiruvlarida unutiladi; `exclude` sozlama, kafolat emas |
| `SecretStr` | ⚠ Foydali (`repr` da `**********`), lekin `get_secret_value()` bir joyda chaqirilsa oshkor bo'ladi. **Ichki DTO'da ishlatiladi**, javob modelida emas |
| **Javob modelida maydon yo'q** | ✅ **TANLANDI** — chiqara olmaslik uchun chiqadigan narsa bo'lmasin |

**Darvoza testi:** `tests/integration/test_nvr_credentials.py::test_password_never_in_any_response` — NVR bilan bog'liq **har bir** endpointga so'rov yuboradi va xom javob tanasida parol satri **yo'qligini** tekshiradi. Yangi endpoint qo'shilganda `tests/tenancy/test_route_coverage.py` naqshi bo'yicha ro'yxatga qo'shiladi.

**Ikkinchi darvoza:** `test_password_never_in_audit` — `audit_log.changes` JSONB ichida parol qiymati bo'lmasligi. ⚠ **Nozik joy:** `fn_audit_row()` DB triggeri `to_jsonb(NEW)` yozadi, ya'ni **shifrlangan bayt** auditga tushadi. Bu ochiq matn emas, lekin baribir noto'g'ri — shifrmatn qatori foydasiz shovqin va u kalit buzilganda tarixiy parollarni beradi. **Yechim:** triggerda `password_encrypted` ustunini istisno qilish (`AUDITED_TABLES` reyestriga ustun-istisno ro'yxati qo'shiladi) yoki parolni **alohida jadvalga** (`nvr_credentials`) ajratib, uni audit triggeridan chiqarish. **Tavsiya: alohida jadval** — u RLS, GRANT va audit uchun bir vaqtda toza chegarani beradi.

#### Nega Postgres `pgcrypto` emas

| Variant | Verdikt |
|---------|---------|
| **Ilova qatlamida Fernet** | ✅ **TANLANDI** — kalit ilova muhitida, DB'da emas. SC#4 aynan shuni talab qiladi |
| `pgcrypto` + DB'dagi kalit | ❌ Kalit DB'da → bazaga kirgan odam parolni ochadi. **SC#4 ni buzadi** |
| `pgcrypto` + har so'rovda uzatiladigan kalit | ❌ Kalit SQL matnida → `pg_stat_statements` va DB loglarida ko'rinadi |
| Fernet — AES-128-CBC + HMAC-SHA256, IV va vaqt tamg'asi bilan | ✅ Tayyor, tekshirilgan konstruksiya — **hand-roll qilinmaydi** |

---

### C.11 — WireGuard split-tunnel va "yagona yo'l" isboti (SC#5, CAM-02)

#### Topologiya

```
┌─ Contabo VPS ────────────────────────────────┐        ┌─ Karmana bozori ─────────┐
│                                              │        │                          │
│  wg0: 10.10.0.1/24                           │        │  Mini-PC / OpenWrt       │
│   AllowedIPs = 10.10.0.2/32, 192.168.1.0/24  │◄───────┤  wg0: 10.10.0.2/24       │
│                ▲                             │  UDP   │  AllowedIPs = 10.10.0.1/32│
│                └── FAQAT shu ikkisi.         │ 51820  │  PersistentKeepalive = 25 │
│                    0.0.0.0/0 HECH QACHON     │        │  Endpoint = vps:51820     │
│                                              │        │            │             │
│  ┌── wireguard (network_mode: host) ───────┐ │        │            ▼             │
│  │  NET_ADMIN, /lib/modules:ro             │ │        │  NVR 192.168.1.64:80/554 │
│  └─────────────────────────────────────────┘ │        │  (internetga OCHIQ EMAS) │
│  ┌── go2rtc ─────────┐  ┌── core-api ─────┐  │        └──────────────────────────┘
│  │ RTSP → WebRTC/HLS │  │ ISAPI (httpx)   │  │
│  └───────────────────┘  └─────────────────┘  │
└──────────────────────────────────────────────┘
```

#### `AllowedIPs` — CLAUDE.md ning qat'iy qoidasi

> **VPS peer'ida `AllowedIPs` faqat NVR subneti bo'lishi kerak (masalan `192.168.1.0/24`), hech qachon `0.0.0.0/0`.** To'liq tunnel VPS'ning **butun** chiquvchi trafigini bozor DSL'idan o'tkazardi — Telegram, Let's Encrypt va foydalanuvchilar trafigi **birga o'lardi**. [CITED: CLAUDE.md]

WireGuard'da `AllowedIPs` **ikki vazifani birga** bajaradi va bu eng ko'p chalkashtiradigan joy:

| Vazifa | Ma'nosi |
|--------|---------|
| **Marshrutlash** (chiqishda) | Bu manzillarga trafik **shu peer'ga** yuboriladi |
| **Kripto-marshrutlash** (kirishda) | Bu peer'dan **faqat shu manzillardan** kelgan paket qabul qilinadi; qolgani **tashlanadi** |

Ikkinchisi bizning xavfsizlik da'vomiz: bozor tomonidagi qurilma buzilsa ham, u tunneldan `192.168.1.0/24` dan tashqari manba bilan paket yubora **olmaydi**.

#### Docker'da WireGuard

```yaml
  wireguard:
    profiles: ["vpn"]
    image: linuxserver/wireguard:1.0.20250521    # yoki plain wg-quick
    network_mode: host                # <-- host kernel modulini ishlatadi
    cap_add: [NET_ADMIN, SYS_MODULE]
    volumes:
      - ./ops/wireguard:/config
      - /lib/modules:/lib/modules:ro  # <-- userspace emas, kernel implementatsiyasi
    sysctls:
      net.ipv4.conf.all.src_valid_mark: 1
    restart: unless-stopped
```

| Qaror | Sabab |
|-------|-------|
| `network_mode: host` | `wg0` **xost** tarmoq nomlar fazosida yaratiladi → barcha konteynerlar (`go2rtc`, `core-api`) uni oddiy marshrut orqali ishlatadi. Alohida namespace'da bo'lsa har bir konteyner uchun `network_mode: service:wireguard` kerak bo'lardi |
| `/lib/modules:ro` | Xost kernel moduli (tez) ishlatiladi, `wireguard-go` userspace (sekin) emas |
| `SYS_MODULE` | Modulni yuklash uchun. Xostda `modprobe wireguard` oldindan bajarilgan bo'lsa **olib tashlash mumkin** — imtiyozni kamaytirish uchun **tavsiya etiladi** |
| `profiles: ["vpn"]` | Dev mashinada (sim bilan) VPN kerak emas |
| ⚠ **Litsenziya** | `linuxserver/wireguard` — GPL-2.0 (WireGuard'ning o'zi). **Alohida, o'zgartirilmagan tarmoq servisi** — Postgres bilan bir xil poza. AGPL emas → CLAUDE.md cheklovini buzmaydi |

#### "Tunnel yagona yo'l" ni **qanday isbotlash** (SC#5) — nozik joy

SC#5: *"tunnel o'chirilsa ulanish uziladi va NVR internetdan to'g'ridan-to'g'ri ochiq emas."*

Sodda test — "tunnelni o'chir, ulanish uzilishini ko'r" — **CI'da bajarilmaydi va yolg'on ishonch beradi**: CI'da tunnel umuman yo'q, ya'ni test har doim "uzildi" deb o'tadi va **hech nima isbotlamaydi**.

To'g'ri yondashuv — da'voni **uchta mustaqil, tekshiriladigan qismga** ajratish:

| # | Da'vo | Qanday isbotlanadi | Qayerda |
|---|-------|--------------------|---------|
| **1** | NVR manzili **xususiy** (RFC 1918) subnetda | `nvr_devices.host` uchun **DB CHECK / ilova validatsiyasi**: ommaviy IP rad etiladi (`nvr_host_must_be_private`) | ✅ **Unit test, CI'da** |
| **2** | `AllowedIPs` da `0.0.0.0/0` **YO'Q** | `ops/wireguard/wg0.conf` ni parse qiladigan test | ✅ **Unit test, CI'da** |
| **3** | Marshrut haqiqatan tunnel orqali ketadi | `ip route get <nvr_ip>` → chiquvchi interfeys `wg0` bo'lishi | ⚠ **Faqat VPS'da** — deploy smoke-testi |

**Nega bu yaxshiroq:** 1 va 2 **bugun, uskunasiz** ishlaydi va aynan **regressiya** xavfini (kimdir keyinroq ommaviy IP kiritadi yoki `AllowedIPs` ni kengaytiradi) tutadi. 3 esa bir martalik deploy tekshiruvi.

> ⚠ **Muhim nuance:** 1-qoida ("faqat xususiy IP") **sim'ni sindirmasligi** kerak. `nvr-sim` compose tarmog'ida `172.16-31.x` (RFC 1918) manzilda turadi va **DNS nomi** `nvr-sim` bo'ladi. Validator **hostname'ni ham** qabul qilishi kerak (`nvr-sim`, `.local`, `.internal`) — faqat **marshrutlanadigan ommaviy IP** rad etiladi. Aks holda sim ishlamas edi va biror kishi validatorni butunlay o'chirib qo'yardi.

**Qo'shimcha qatlam:** `core-api` va `go2rtc` konteynerlari **`AllowedIPs` dan tashqariga chiqmasligini** ta'minlash uchun Docker tarmog'ida chiquvchi qoida yozish mumkin, lekin bu MVP uchun ortiqcha — asosiy kafolat WireGuard'ning kripto-marshrutlashida.

---

### C.12 — CGNAT: bozor tomoni "rozetkaga ulaydi"

ROADMAP aniq aytadi: *"CGNAT holati mahsulot muammosi emas — bozor tomonida oldindan sozlangan WireGuard qurilmasi `PersistentKeepalive` bilan o'zi uyga qo'ng'iroq qiladi. Admin uni faqat rozetkaga ulaydi."*

#### Nega CGNAT muammo emas

CGNAT (Carrier-Grade NAT) — bozorning ommaviy IP'si yo'q va unga **tashqaridan ulanib bo'lmaydi**. Lekin WireGuard **peer-to-peer, klient-server emas**: agar bozor tomoni **birinchi** paket yuborsa, NAT jadvalida yo'l ochiladi va VPS o'sha yo'l orqali javob bera oladi.

`PersistentKeepalive = 25` har 25 soniyada bo'sh paket yuboradi — bu NAT yozuvini tirik saqlaydi (odatiy NAT timeout'i 30–120 s).

#### Konfiguratsiya

**Bozor tomoni (oldindan sozlangan qurilma):**

```ini
[Interface]
PrivateKey = <bozor-qurilmasining maxfiy kaliti>
Address    = 10.10.0.2/24

[Peer]
PublicKey           = <VPS ochiq kaliti>
Endpoint            = vps.sbozor.uz:51820
AllowedIPs          = 10.10.0.1/32          # FAQAT VPS — bozor trafigi tunneldan o'tmaydi
PersistentKeepalive = 25                    # <-- CGNAT'ni yengadigan yagona qator
```

**VPS tomoni:**

```ini
[Interface]
PrivateKey = <VPS maxfiy kaliti>
Address    = 10.10.0.1/24
ListenPort = 51820

[Peer]
# Karmana
PublicKey  = <bozor qurilmasi ochiq kaliti>
AllowedIPs = 10.10.0.2/32, 192.168.1.0/24   # <-- 0.0.0.0/0 HECH QACHON
# Endpoint YOZILMAYDI — bozor o'zi qo'ng'iroq qiladi, manzili o'zgaruvchan
```

> ⚠ VPS peer'ida **`Endpoint` yozilmaydi**. Bu CGNAT topologiyasining mohiyati: VPS bozorning manzilini bilmaydi va bilishi ham shart emas — u birinchi handshake'dan keyin o'rganadi.

#### On-site odam nima qiladi

| Qadam | Kim |
|-------|-----|
| 1. Qurilmani rozetkaga ulash | On-site (har kim) |
| 2. Ethernet kabelini NVR bilan bir tarmoqqa ulash | On-site |
| 3. (hammasi) | — |

Kalitlar, `wg0.conf` va NVR subneti **jo'natishdan oldin** yoziladi. Bu ROADMAP ning "muhandis aralashuvi qabul qilinmaydi" qoidasining tarmoq tomonidagi ifodasi.

#### Bir nechta bozor

Har bozor — **alohida peer** va **alohida `10.10.<N>.0/24`** subneti. `AllowedIPs` har peer uchun o'sha bozorning NVR subnetini beradi. ⚠ **To'qnashuv xavfi:** ikkala bozor ham `192.168.1.0/24` ishlatsa VPS marshrut jadvali chalkashadi. **Yechim:** har bozorga tunnel ichida noyob subnet berish (bozor tomonida `1:1 NAT`) yoki onboarding'da subnetni yozib olib to'qnashuvni tekshirish. **Bu fazada:** `nvr_devices` ga `tunnel_subnet` maydoni va **global noyoblik tekshiruvi** — arzon ilgak, keyin retrofit qilish qimmat (OQ-4).

---

## D. Jonli ko'rish (CAM-03)

### D.13 — go2rtc integratsiyasi va avtorizatsiya (SC#6)

#### ⚠ Eng muhim topilma: go2rtc API'si = masofaviy kod ijrosi

Frigate loyihasidagi xavfsizlik ogohnomasi (**CVSS 9.1 Critical**) aynan bizning ishlatmoqchi bo'lgan naqshimizga tegishli:

> *"Authenticated Admin Can Achieve RCE via go2rtc Stream API — `exec:` Filter Not Enforced at API Layer."* `PUT /api/go2rtc/streams/{name}` `src` parametrini go2rtc'ga **filtrsiz** uzatgan; `exec:` protokoli esa **ixtiyoriy tizim buyrug'ini** oqim manbai sifatida ro'yxatga olishga imkon beradi. Natija: **ikkita HTTP so'rov bilan konteyner ichida root sifatida RCE.** [CITED: GHSA-wwww-5h25-jf98, CVSS:3.1/AV:N/AC:L/PR:H/UI:N/S:C/C:H/I:H/A:H = 9.1]

**Bizning fazamiz uchun uchta majburiy oqibat:**

| # | Qoida | Amalda |
|---|-------|--------|
| **1** | **go2rtc HTTP API'si (1984) foydalanuvchiga HECH QACHON ochilmaydi** — na to'g'ridan-to'g'ri, na proxy orqali | Nginx'da `/api/streams`, `/api/config`, `/api/restart` yo'llari **bloklanadi**. Faqat `core-api` compose tarmog'idan boradi |
| **2** | `core-api` go2rtc'ga yuboradigan `src` **allow-list bilan tekshiriladi** | Faqat `rtsp://` sxemasi; `exec:`, `ffmpeg:`, `echo:` va boshqalar **rad etiladi**. `src` foydalanuvchi kiritmasidan **hech qachon** to'g'ridan-to'g'ri qurilmaydi |
| **3** | Sim go2rtc'i `exec:` ishlatadi — **lekin faqat statik config faylidan**, API'dan emas | `ops/go2rtc/go2rtc.sim.yaml` — o'qishga mo'ljallangan mount. Bu farq muhim: config'dagi `exec:` xavfsiz, API'dagi `exec:` — RCE |

```python
_ALLOWED_STREAM_SCHEME = "rtsp://"

def assert_safe_go2rtc_src(src: str) -> None:
    """go2rtc `src` — FAQAT rtsp://. `exec:`/`ffmpeg:` = RCE (GHSA-wwww-5h25-jf98)."""
    if not src.startswith(_ALLOWED_STREAM_SCHEME):
        raise ValueError("unsafe_go2rtc_source")
```

**Darvoza testi:** `tests/unit/test_go2rtc_client.py::test_rejects_exec_source` — `exec:`, `ffmpeg:`, `echo:` bilan boshlanuvchi `src` rad etilishi.

#### Dinamik oqim ro'yxatga olish (restart'siz)

Kamera kashf qilinganda go2rtc'ni qayta ishga tushirish **qabul qilib bo'lmaydi** — u boshqa bozorlarning ko'rishini uzardi. go2rtc HTTP API'si buni qo'llaydi:

| Amal | So'rov | Manba |
|------|--------|-------|
| Qo'shish | `PUT /api/streams?name=<nom>&src=<rtsp-url>` | [CITED: AlexxIT/go2rtc issue #1151] |
| Yangilash | `PATCH /api/streams?name=<nom>&src=<rtsp-url>` | [CITED: issue #1151] |
| O'chirish | `DELETE /api/streams?src=<nom>` | [CITED: issue #1592 / dashboard kodi] |
| Ro'yxat | `GET /api/streams` | [CITED: go2rtc API] |

⚠ **Doimiylik:** `PUT /api/streams` oqimni **xotirada** qo'shadi. go2rtc qayta ishga tushsa u yo'qoladi. Ikki variant:

| Variant | Verdikt |
|---------|---------|
| **`core-api` startup'da barcha kameralarni qayta ro'yxatga oladi** (`lifespan` da yoki birinchi murojaatda lazy) | ✅ **TANLANDI** — DB **yagona haqiqat manbai** bo'lib qoladi; go2rtc konfiguratsiyasi **hosila**. 2-fazadagi "usta holati — domen ma'lumotining o'zi" falsafasi bilan bir xil |
| `PATCH /api/config` bilan YAML'ga yozish | ❌ Ikkinchi haqiqat manbai; drift; `exec:` yozish yuzasini kengaytiradi |

**Eng sodda va eng ishonchli shakl — lazy:** direktor kamerani ko'rmoqchi bo'lganda `core-api` (a) `GET /api/streams` bilan oqim borligini tekshiradi, (b) yo'q bo'lsa `PUT` qiladi, (c) keyin jonli ko'rish tokenini beradi. Bu startup'dagi 25 ta so'rovni ham, drift'ni ham yo'q qiladi.

#### Avtorizatsiya: go2rtc **tenant tushunmaydi**

go2rtc'da faqat global Basic-auth bor (`api.username/password`) — **bozor tushunchasi yo'q**. Ya'ni go2rtc'ni foydalanuvchiga ochish A bozori direktoriga B bozori kamerasini beradi. SC#6 buni taqiqlaydi.

```
Brauzer ──1── GET /api/v1/cameras/{id}/live-token   (Bearer, RBAC: CAMERA_VIEW, RLS: market)
             ◄── {"url": "/live/webrtc?src=<opaque>&t=<imzolangan-token>", "expires_in": 60}
        ──2── /live/... ──► Nginx ──auth_request──► core-api  /internal/live-authz
                                                     ├─ token imzosi + muddati
                                                     ├─ camera_id → market_id
                                                     └─ 204 / 403
                              └──(204 bo'lsa)──► go2rtc:1984
```

| Element | Qaror | Sabab |
|---------|-------|-------|
| **Oqim nomi** | `cam_<uuid4>` — **`market_id` yoki kamera kodi EMAS** | Nom URL'da ko'rinadi; ma'noli nom bozorlar sonini va nomlanish sxemasini oshkor qilardi |
| **Token** | Qisqa muddatli (≤60 s), **imzolangan**, `camera_id` + `market_id` + `user_id` ni o'z ichiga oladi | Uzun muddatli havola **ulashiladi** — SC#6 "avtorizatsiyasiz havola ishlamaydi" deydi |
| **Tekshiruv joyi** | Nginx `auth_request` → `core-api` | go2rtc'da avtorizatsiya mantiqi **yo'q va bo'lishi ham kerak emas** |
| **`CAMERA_VIEW` huquqi** | ✅ **`rbac.py` da ALLAQACHON bor** — `DIRECTOR` va `MARKET_ADMIN` da | 1-fazadan meros. ⚠ `PLATFORM_ADMIN` da **YO'Q** — Wave 0 bo'shlig'i (pastga qarang) |
| **Jonli ko'rish auditi** | `Depends(audit_read("cameras", reason="live_view"))` | 2-fazadagi D-09 naqshi. "Kim, qachon, qaysi kamerani ko'rdi" — nizo paytida kerak |

> ⚠ **Wave 0 bo'shlig'i (kod o'qildi):** `services/core-api/app/security/rbac.py:130-143` — `Role.PLATFORM_ADMIN` da `CAMERA_VIEW` **yo'q**. Lekin self-service qoidasi bo'yicha **aynan platforma admini** yangi bozorni ulaydi va kameralar topilganini **ko'rishi kerak**. Bu 2-fazadagi Pitfall 6 ning ayni takrori (o'shanda `STALL_MANAGE` yetishmasdi). Bundan tashqari **`CAMERA_MANAGE` huquqi umuman mavjud emas** — NVR qo'shish/kashfiyot ishga tushirish uchun yangi huquq kerak. Ikkalasi ham birinchi migratsiyadan **oldin** yopiladi va `frontend/src/lib/rbac.ts` ko'zgusi qo'lda sinxronlanadi (`rbac.py` docstring talabi).

#### WebRTC vs HLS/MSE — transport tanlovi

| Transport | Kechikish | Proxy'dan o'tadimi | Verdikt |
|-----------|-----------|--------------------|---------|
| **WebRTC** | ~0.5 s | ❌ **UDP 8555 to'g'ridan-to'g'ri kerak** (HTTP proxy'dan o'tmaydi) | ✅ Standart — CLAUDE.md aniq aytadi |
| **MSE** (WebSocket) | ~1–2 s | ✅ Nginx `proxy_pass` + WS upgrade | ✅ **Fallback** — UDP bloklangan tarmoqda |
| **HLS** | 5–15 s | ✅ | ⚠ Oxirgi chora; "jonli" his bermaydi |
| MJPEG | past | ✅ | ❌ Bandwidth halokati |

go2rtc'ning `video-stream` veb-komponenti **avtomatik tanlaydi** (WebRTC → MSE → HLS). Tavsiya: shu tartibni saqlash va UI'da qaysi transport ishlayotganini ko'rsatish — dala diagnostikasi uchun.

CLAUDE.md eslatmasi: *"go2rtc WebRTC needs **UDP 8555** open directly. Proxy only go2rtc's HTTP API/HLS through Nginx."* ⚠ Lekin yuqoridagi 1-qoida bilan birga o'qing: **HTTP API proxy qilinmaydi** — faqat `/live/` signalling yo'li (`/api/ws`) proxy'dan o'tadi, `/api/streams` esa **bloklanadi**.

---

### D.14 — Sessiya byudjeti: go2rtc va NVR chegarasi

A.5 dagi qaror bu yerda amalga oshadi.

| Xulq | Qiymat |
|------|--------|
| go2rtc oqimni **qachon ochadi** | **Faqat birinchi tomoshabin ulanganda** (lazy). Tomoshabin ketganda yopadi |
| 25 kamera ro'yxatga olingan, 0 tomoshabin | **0 ta RTSP sessiyasi** NVR'ga |
| 1 direktor 1 kamerani ko'radi | 1 ta sessiya (sub-oqim) |
| 3 foydalanuvchi **bitta** kamerani ko'radi | **1 ta** sessiya — go2rtc bitta manbani ko'p iste'molchiga ulashadi |
| 4-faza kadr olish | `/api/frame.jpeg` — **mavjud** oqimdan; yangi sessiya yo'q |

Bu go2rtc'ning **eng katta arxitekturaviy afzalligi** bu loyihada: 25 kamerani ro'yxatga olish NVR byudjetiga **hech qanday** doimiy yuk qo'ymaydi.

⚠ **Nozik joy (4-faza uchun ilgak):** kadr olish jadvali 25 kamerani **bir vaqtda** so'rasa, go2rtc 25 ta oqimni **birdan** ochadi → A.5 dagi bitreyt chegarasiga urilinadi. Bu **4-fazaning muammosi**, lekin uning yechimi (`stagger` — kadr olishni vaqt bo'yicha yoyish) shu yerda hujjatlashtiriladi, chunki uni keyin topish qimmat.

**Bu fazada o'lchanadigan narsa:** sim'da `stream_limit: 4` rejimi bilan 6 kamerani birdan ochishga urinish → 5-chi va 6-chi rad etiladi → `nvr_stream_limit` xatosi va **tushunarli xabar** chiqadi. Bu A.5 heuristikasining yagona sinovi.

---

## E. Ma'lumot modeli va arxitektura

### E.15 — Sxema

Barcha jadvallar **tenant jadvali** naqshiga bo'ysunadi (2-faza S-1): `market_id` + RLS `ENABLE` **va** `FORCE` + tenant policy + `market_id` bilan boshlanuvchi indekslar + composite FK. `tests/tenancy/test_meta.py` ning beshta invarianti **avtomatik** qo'llanadi.

#### `nvr_devices` — NVR qurilmasi

| Ustun | Tip | Izoh |
|-------|-----|------|
| `id` | `uuid` PK | `uuidv7()` (PG18 native) |
| `market_id` | `uuid` NOT NULL | RLS kaliti |
| `host` | `text` NOT NULL | IP yoki hostname. **Ommaviy IP rad etiladi** (C.11) |
| `port` | `int` NOT NULL DEFAULT 80 | ISAPI HTTP porti |
| `use_tls` | `bool` NOT NULL DEFAULT false | HTTPS ISAPI |
| `rtsp_port` | `int` NULL | `adminAccesses` dan **kashf etiladi**; NULL = hali skan qilinmagan |
| `rtsp_port_assumed` | `bool` NOT NULL DEFAULT false | `true` = 554 fallback ishlatildi (A.2) |
| `username` | `text` NOT NULL | Ochiq matn — sir emas |
| `model` | `text` NULL | `deviceInfo/model` |
| `serial_number` | `text` NULL | **Qurilmaning barqaror identifikatori** |
| `firmware_version` | `text` NULL | Diagnostika |
| `device_type` | `text` NULL | `NVR` / `IPCamera` — kashfiyot yo'lini belgilaydi |
| `tunnel_subnet` | `cidr` NULL | C.12 — bozorlar orasidagi to'qnashuvni oldini olish |
| `last_discovery_at` | `timestamptz` NULL | |
| `created_at`/`updated_at` | `timestamptz` | 1-faza naqshi |

`UNIQUE (market_id, host, port)` — bitta bozorda bitta NVR ikki marta qo'shilmaydi.

#### `nvr_credentials` — **alohida jadval** (C.10 dagi audit sababidan)

| Ustun | Tip | Izoh |
|-------|-----|------|
| `nvr_id` | `uuid` PK/FK | 1:1 |
| `market_id` | `uuid` NOT NULL | RLS + composite FK `(market_id, nvr_id)` |
| `password_encrypted` | `bytea` NOT NULL | Fernet token |
| `key_version` | `smallint` NOT NULL DEFAULT 1 | Rotatsiya kuzatuvi |
| `updated_at` | `timestamptz` | |

**Nega alohida:** (1) `fn_audit_row()` triggeri **bu jadvalga ulanmaydi** — shifrmatn auditga tushmaydi; (2) parol o'zgarishi fakti `nvr_devices` auditida "credentials_updated" hodisasi sifatida **qiymatsiz** yoziladi; (3) kelajakda `sbozor_app` ga bu jadvalga tor GRANT berish mumkin.

#### `cameras` — kamera (kanal) yozuvi

| Ustun | Tip | Izoh |
|-------|-----|------|
| `id` | `uuid` PK | 5-faza zonalari va 4-faza snapshotlari shunga bog'lanadi → **hech qachon o'chirilmaydi** |
| `market_id` | `uuid` NOT NULL | RLS |
| `nvr_id` | `uuid` NOT NULL | composite FK `(market_id, nvr_id)` |
| `channel_no` | `int` NOT NULL | **Identifikatsiya kaliti** (A.4) |
| `stream_name` | `text` NOT NULL UNIQUE | `cam_<uuid4>` — go2rtc'dagi nom (D.13) |
| `name` | `text` NOT NULL | NVR'dan yoki admin bergan |
| `name_overridden` | `bool` NOT NULL DEFAULT false | **SC#2: "mavjudi tegilmaydi"** |
| `status` | `text` NOT NULL | `online` / `offline` / `unknown` |
| `has_substream` | `bool` NOT NULL DEFAULT true | `{ch}02` mavjudmi (A.2) |
| `source_ip` | `inet` NULL | Kuzatiladigan atribut |
| `source_model` | `text` NULL | Kuzatiladigan atribut |
| `first_seen_at` | `timestamptz` NOT NULL | **Hech qachon yangilanmaydi** |
| `last_seen_at` | `timestamptz` NOT NULL | Har skanda |

**`UNIQUE (market_id, nvr_id, channel_no)`** — SC#2 dagi "dublikat yaratilmaydi" ning **DB kafolati**. Ilova qatlamidagi tekshiruv yetarli emas (2-fazadagi `stall_code_registry` falsafasi).

> `rtsp_url` ustuni **YO'Q** — URL hosila (A.2).

#### `nvr_discovery_runs` — kashfiyot yugurishi

| Ustun | Tip | Izoh |
|-------|-----|------|
| `id` | `uuid` PK | Frontend shu bo'yicha poll qiladi |
| `market_id`, `nvr_id` | `uuid` | RLS + composite FK |
| `status` | `text` | `queued` / `running` / `succeeded` / `failed` |
| `started_at`/`finished_at` | `timestamptz` | |
| `channels_found` / `channels_added` / `channels_marked_offline` | `int` | **SC#2 ni kuzatiladigan qiladi** |
| `error_code` | `text` NULL | A.3 taksonomiyasi — **i18n kaliti** |
| `error_detail` | `jsonb` NULL | Xom diagnostika (drift soniyalari, xom RTSP javobi). ⚠ **`mask_sensitive` dan o'tadi** |
| `triggered_by` | `uuid` | Kim ishga tushirdi |

`error_code` — **kod, matn emas**. Frontend uni uch tilga tarjima qiladi (`nvr.error.clock_drift` va h.k.), CLAUDE.md ning "3 til majburiy" qoidasi bo'yicha.

#### Audit trailiga nima tushadi

| Hodisa | Mexanizm | Sabab |
|--------|----------|-------|
| NVR qo'shildi / manzil o'zgardi | `fn_audit_row()` DB triggeri | D-10: xom SQL yo'li ham qamraladi |
| **Parol o'zgardi** | Ilova qatlami, `action='nvr_credentials_updated'`, **qiymatsiz** | Shifrmatn ham auditga tushmasin |
| Kashfiyot ishga tushdi/tugadi | Ilova qatlami (`triggered_by`, natija) | Kim, qachon, nima topdi |
| Kamera qo'shildi / offline / `source_changed` | `fn_audit_row()` triggeri | 5-fazada zona yaroqsizligining sababi shu yerdan topiladi |
| **Jonli ko'rish** | `Depends(audit_read("cameras", reason="live_view"))` | Nizo paytida "kim ko'rdi" |
| Nomni qo'lda o'zgartirish | Trigger (`name`, `name_overridden`) | |

> ⚠ `AUDITED_TABLES` reyestriga `nvr_devices` va `cameras` **qo'shiladi**, `nvr_credentials` **QO'SHILMAYDI**. `tests/tenancy/test_meta.py::test_audited_tables_have_trigger` buni majburlaydi. `FINANCIAL_TABLES` ga **hech biri qo'shilmaydi** (pul ustuni yo'q — 2-fazadagi Pitfall 3 ning takrorlanishidan saqlanish).

---

### E.16 — Kashfiyot qayerda ishlaydi: inline emas, **job**

#### Byudjet hisobi

```
Bitta ISAPI so'rov (Digest) = 2 borish  (401 challenge + autentifikatsiyalangan)
Tunnel + NVR javob vaqti    ≈ 100–500 ms har borish (DSL, CGNAT ortida)

Kashfiyot:
  deviceInfo               1 so'rov
  adminAccesses            1
  InputProxy/channels      1
  InputProxy/.../status    1
  Streaming/channels/{ch}02 tekshiruvi   × 25 kanal      <-- eng qimmat
  ────────────────────────────────────────────────
  ≈ 29 so'rov × 2 borish × 300 ms  ≈  17 soniya  (yaxshi holatda)
  Sekin NVR / timeout / retry bilan  →  60+ soniya
```

**HTTP so'rovi ichida bu qabul qilib bo'lmaydi:** brauzer/proxy timeout'i, `uvicorn --workers 1` (compose.yaml da qat'iy) — bitta uzoq so'rov **butun API'ni bloklaydi**.

#### ⛔ `arq` BU YERDA ISHLAMAYDI — tasdiqlangan versiya to'qnashuvi

> **Bu tadqiqotning eng qimmatli topilmasi.** CLAUDE.md navbat sifatida `arq 0.28.0` ni belgilaydi, lekin u **`core-api` ga o'rnatilmaydi**:

```
arq 0.28.0        →  redis[hiredis]<6,>=4.2.0
core-api (mavjud) →  redis[hiredis]==8.0.1
```

**Empirik tasdiq (2026-08-02, `pip install arq` bajarildi):**

```
Installing collected packages: tenacity, redis, hiredis, respx, arq
  Attempting uninstall: redis
    Found existing installation: redis 8.0.0
    Uninstalling redis-8.0.0:                    <-- arq redis'ni 5.3.1 GA TUSHIRDI
Successfully installed arq-0.28.0 redis-5.3.1 ...
```

`importlib.metadata` bilan tekshirildi: `arq 0.28.0 → redis[hiredis]<6,>=4.2.0`. [VERIFIED: mahalliy o'rnatish + paket metama'lumoti, 2026-08-02]

⚠ CLAUDE.md ning "Version Compatibility" jadvali `aiogram ↔ redis<8` to'qnashuvini hujjatlashtirgan, lekin **`arq ↔ redis<6` ni EMAS**. Bu yangi topilma va u rejaga bevosita ta'sir qiladi.

#### Variantlar (to'qnashuv hisobga olingan holda)

| Variant | redis piniga mosmi | Verdikt |
|---------|--------------------|---------|
| **`taskiq 0.12.4` + `taskiq-redis 1.2.3`** | ✅ `redis<9,>=8.0.0` — **`8.0.1` bilan aynan mos** [VERIFIED: PyPI metadata] | ✅ **TANLANDI.** CLAUDE.md uni **allaqachon sanksiyalagan** ("Switch to this if arq goes quiet"). MIT. `taskiq-redis` 2026-06-23, `taskiq` 2026-05-08 — arq'dan faolroq. 4-fazaga **cron** yo'lini ham ochiq qoldiradi |
| `arq 0.28.0` | ❌ `redis<6` — **core-api ni 5.x ga tushiradi** | ❌ **RAD ETILDI.** `redis` ni 5.x ga tushirish CLAUDE.md pinini buzadi va butun `core-api` ni eskiroq klientga qaytaradi — bitta fon-vazifa uchun juda qimmat narx |
| `arq` + `redis>=5,<6` ga tushish | ⚠ Texnik jihatdan ishlaydi (`ratelimit.py`/`deps.py` faqat `get/set/delete/incr/expire` + `RedisError` ishlatadi — hammasi 5.x da bor) | ⚠ **Zaxira variant**, agar `taskiq` abstraksiyasi og'ir deb topilsa. **Yozma deviatsiya** talab qiladi |
| Postgres `SELECT … FOR UPDATE SKIP LOCKED` + `nvr_discovery_runs` | ✅ Yangi bog'liqlik **umuman yo'q** | ⚠ **Kuchli zaxira.** Jadval **baribir kerak** (SC#2 kuzatuvi). Lekin lease/heartbeat (`locked_until`) bilan birga ~80 qator navbat kodi = **hand-roll**. Cron bermaydi (4-fazaga foydasi yo'q) |
| FastAPI `BackgroundTasks` | — | ❌ Jarayon o'lsa job yo'qoladi; holat kuzatilmaydi; `--workers 1` bilan baribir shu jarayonda |
| `asyncio.create_task` | — | ❌ Xuddi shu + boshqarilmaydi |
| Inline, qisqartirilgan (sub-oqim tekshiruvisiz) | — | ⚠ ~4 so'rov ≈ 2.5 s — chegaraviy holatda ishlaydi, lekin sekin NVR'da yiqiladi va SC#3 dagi `slow` stsenariysini bajarmaydi |

> ⚠ **4-faza bilan muvofiqlashtirish (OQ-3).** ROADMAP Phase 4 orkestratsiya mexanizmini (`SKIP LOCKED` vs `arq`) **ochiq savol** deb belgilagan. 3-faza `taskiq` ni tanlashi 4-fazani **bloklamaydi**, lekin **ikki mexanizm saqlanmasligi** kerak: 4-faza boshqa yo'lni tanlasa, 3-faza ham unga ko'chiriladi. Shuning uchun kashfiyot jobi **kutubxonaga kuchsiz bog'langan** qilib yoziladi — sof `async def discover_nvr(nvr_id, run_id) -> None` funksiya, taskiq dekoratori esa faqat **yupqa qobiq**. Ko'chirish narxi shunda ~10 qator bo'ladi.

#### Oqim

```
POST /api/v1/nvr-devices/{id}/discover     require_permission(CAMERA_MANAGE)
  ├─ nvr_discovery_runs ga qator (status='queued')
  ├─ arq ga job qo'yish (nvr_id, run_id, market_id, actor_id)
  └─ 202 Accepted + {"run_id": ...}

GET /api/v1/nvr-devices/{id}/discovery-runs/{run_id}     poll (TanStack Query)
  └─ {"status": "running"|"succeeded"|"failed",
      "channels_found": 6, "channels_added": 6,
      "error_code": null, "error_detail": null}
```

⚠ **Ikkita "birinchi marta" muammosi:**

| Muammo | Yechim |
|--------|--------|
| **arq worker'da tenant konteksti yo'q** | Worker HTTP so'rov emas → `get_tenant_session` ishlamaydi. Job **o'z sessiyasini** ochib `set_tenant_context(market_id=..., actor_kind=ActorKind.SYSTEM)` chaqirishi kerak. `ActorKind` enum'i 1-fazadan mavjud. ⚠ **Bu loyihaning birinchi fon-vazifasi** — naqsh shu yerda o'rnatiladi va 4-faza uni meros oladi |
| **Bir vaqtda ikki skan** | `nvr_discovery_runs` da `UNIQUE ... WHERE status IN ('queued','running')` qisman indeks → ikkinchi so'rov **409** |

#### `arq` worker konteyneri

```yaml
  worker:
    build: {context: ., dockerfile: services/core-api/Dockerfile, target: runtime}
    command: ["taskiq", "worker", "app.worker:broker"]
    environment:
      DATABASE_URL: ${DATABASE_URL}
      VALKEY_URL: ${VALKEY_URL:-redis://cache:6379/0}
      NVR_CREDENTIAL_KEY: ${NVR_CREDENTIAL_KEY}
      TZ: Asia/Tashkent
    depends_on: {db: {condition: service_healthy}, cache: {condition: service_healthy}}
```

⚠ Bu **to'rtinchi konteyner**, lekin **uchinchi servis emas**: `core-api` kod bazasining boshqa entrypoint'i (`migrate` va `tests` bilan bir xil naqsh). CLAUDE.md ning "aynan 3 ta servis" cheklovi buzilmaydi.

#### "Ulanishni tekshirish" (CAM-01) — **inline qoladi**

Bu **boshqa amal**: 1–2 ISAPI so'rov (`deviceInfo` + soat farqi tekshiruvi) ≈ 1 soniya. U inline bo'lishi **kerak** — admin tugma bosgach darhol javob kutadi.

```
POST /api/v1/nvr-devices/test-connection     # yozuv YARATILMAYDI
  body: {host, port, username, password}
  → 200 {"ok": true,  "model": "DS-7616NI-K2", "device_type": "NVR",
          "channels_preview": 6, "clock_drift_seconds": 12}
  → 200 {"ok": false, "error_code": "nvr_clock_drift",
          "error_detail": {"drift_seconds": 420, "device_time": "..."}}
```

> ⚠ **Xavfsizlik qoidasi:** bu endpoint parolni **qabul qiladi** (tanada), lekin uni **qaytarmaydi** va **yozmaydi**. `censor_secrets` filtri `nvr_password` kalitini allaqachon biladi. Endpoint **rate-limit ostida** bo'lishi kerak: aks holda u NVR'ga qarshi parol-brute-force vositasiga aylanadi **va** hisobni qulflaydi (A.3). 1-fazadagi `app/security/ratelimit.py` qayta ishlatiladi.

#### Frontend oqimi (SC#1 — "faqat manzil va parol")

```
1. [Kamera bo'limi] → "NVR ulash"
2. Forma: manzil · port(80) · login · parol            ← ADMIN KIRITADIGAN YAGONA NARSA
3. [Ulanishni tekshirish] → inline, ≤2 s
     ✅ "DS-7616NI-K2 topildi · 6 kanal · soat farqi 12 s"
     ❌ "NVR soati 7 daqiqa farq qilyapti → NTP'ni yoqing"   (A.3, uch tilda)
4. [Saqlash va kameralarni topish] → 202 + poll
5. Natija: "6 ta kamera qo'shildi" + jonli ko'rish tugmalari bilan ro'yxat
     — QO'LDA BIRORTA RTSP URL YOZILMAYDI
```

`nuqs` bilan `run_id` URL'da saqlanadi (2-fazadagi usta naqshi) — sahifa yangilanganda poll davom etadi.


---

## Standard Stack

### Yangi paketlar — `services/core-api`

| Kutubxona | Versiya | Litsenziya | Maqsad | Nega standart |
|-----------|---------|-----------|--------|---------------|
| `taskiq` | **0.12.4** (2026-05-08) | MIT | Fon-vazifa (kashfiyot jobi) | CLAUDE.md **allaqachon sanksiyalagan** muqobil ("Switch to this if arq goes quiet"). `arq` redis to'qnashuvi tufayli ishlamaydi (E.16) [VERIFIED: PyPI + mahalliy o'rnatish] |
| `taskiq-redis` | **1.2.3** (2026-06-23) | MIT | Valkey brokeri + natija backend'i | `redis<9,>=8.0.0` — `core-api` ning `redis==8.0.1` piniga **aynan mos** [VERIFIED: PyPI `requires_dist`] |
| `tenacity` | **9.1.4** | Apache-2.0 | ISAPI so'rovlari ichidagi retry | CLAUDE.md'da qulflangan. ⚠ **Faqat tarmoq xatolarida** — `401` da HECH QACHON (A.3: hisob qulflanadi) [VERIFIED: PyPI] |

### Yangi dev-paketlar — `services/core-api` `[dependency-groups] dev`

| Kutubxona | Versiya | Litsenziya | Maqsad |
|-----------|---------|-----------|--------|
| `respx` | **0.23.1** (2026-04-08) | BSD-3-Clause | ISAPI **parser** unit testlari — `httpx` transportini almashtiradi. ⚠ Digest handshake'ni sinamaydi (B.6) — u `nvr-sim` ning ishi |

### Allaqachon mavjud va **qayta ishlatiladi** (yangi paket kerak emas)

| Kutubxona | Versiya | Bu fazada nima uchun |
|-----------|---------|----------------------|
| `httpx` | 0.28.1 (**dev guruhida** — ⚠ `main` ga ko'chirilishi kerak) | ISAPI klienti + `httpx.DigestAuth` |
| `cryptography` | 49.0.0 | **Fernet / MultiFernet** — NVR parollari (C.10) |
| `structlog` | 26.1.0 | `censor_secrets` `nvr_password`/`rtsp_password` ni **allaqachon biladi** |
| `redis[hiredis]` | 8.0.1 | Valkey — taskiq brokeri va mavjud kesh |
| `pydantic` / `pydantic-settings` | 2.13.4 / 2.14.2 | `NVR_CREDENTIAL_KEY` validatsiyasi |
| `sqlalchemy` / `alembic` / `alembic-utils` | 2.0.51 / 1.18.5 / 0.8.8 | 4 ta yangi tenant jadvali + RLS policy'lari |
| **`fastapi`** | 0.140.13 | ⚠ **`nvr-sim` ham shuni ishlatadi** — sim yangi bog'liqlik keltirmaydi |

> ⚠ **`httpx` bugun `[dependency-groups] dev` da** (`pyproject.toml:53`). ISAPI klienti — **ishlab chiqarish kodi**, ya'ni `httpx` `[project] dependencies` ga **ko'chirilishi shart**. Aks holda `uv sync --frozen --no-dev` bilan qurilgan prod image'da `ImportError` bo'ladi va bu **faqat deploy paytida** ko'rinadi. Wave 0 bandi.

### Konteyner image'lari

| Image | Versiya | Litsenziya | Maqsad |
|-------|---------|-----------|--------|
| `alexxit/go2rtc` | **1.9.14** | MIT | Jonli ko'rish (prod) **va** sim RTSP manbai |
| `linuxserver/wireguard` | 1.0.x | GPL-2.0 (WireGuard) | VPN sidecar. **Alohida, o'zgartirilmagan tarmoq servisi** — AGPL emas, CLAUDE.md cheklovini buzmaydi |

### Alternatives Considered

| O'rniga | Ishlatish mumkin edi | Trade-off / qachon o'tiladi |
|---------|----------------------|------------------------------|
| `taskiq` + `taskiq-redis` | **`arq 0.28.0`** | ❌ **BLOKLANGAN** — `redis<6` vs `redis==8.0.1` (E.16, empirik). O'tish sharti: `core-api` ni `redis>=5,<6` ga tushirishga **yozma deviatsiya** berilsa |
| `taskiq` | **Postgres `SKIP LOCKED` + `nvr_discovery_runs`** | Yangi bog'liqlik **yo'q**, jadval baribir kerak. Lekin lease/heartbeat bilan ~80 qator navbat kodi (**hand-roll**) va cron bermaydi. **O'tish sharti:** 4-faza `SKIP LOCKED` ni tanlasa — o'shanda ikkalasi ham unga ko'chadi (OQ-3) |
| Maxsus FastAPI `nvr-sim` | WireMock / Mockoon | Digest challenge'ni to'g'ri bajara olmaydi va holatli (lockout/drift) rejimlarni modellay olmaydi (B.6) |
| Maxsus `nvr-sim` | `respx` / `pytest-httpx` | **Ikkalasi ham ishlatiladi, boshqa qatlamlarda.** `respx` — parser unit testlari; `nvr-sim` — SC#7 E2E darvozasi |
| go2rtc (sim RTSP manbai) | **MediaMTX** (MIT) | Yaxshi vosita, lekin go2rtc allaqachon stekda va CAM-09 uni nomma-nom ko'rsatgan. Yangi bog'liqlik qo'shilmaydi |
| ISAPI kashfiyoti | **ONVIF `GetSnapshotUri` / auto-discovery** | CLAUDE.md ONVIF'ni allaqachon rad etgan; `onvif-zeep` (0.2.12) eskirgan. Faqat noma'lum brendlar uchun kelajakda |
| Ilova qatlamida Fernet | `pgcrypto` | Kalit DB'da bo'lardi → **SC#4 ni buzadi** (C.10) |
| WebRTC (UDP 8555) | MSE / HLS | **Fallback sifatida saqlanadi** — UDP bloklangan tarmoqda go2rtc avtomatik tushadi (D.13) |
| `linuxserver/wireguard` | Plain `wg-quick` xostda | UI kerak bo'lmasa `wg-quick` **soddaroq**. `wg-easy 15.3.0` — CLAUDE.md'da ixtiyoriy deb belgilangan |

**Installation:**

```bash
uv add --project services/core-api "taskiq==0.12.4" "taskiq-redis==1.2.3" "tenacity==9.1.4"
uv add --project services/core-api --dev "respx==0.23.1"
# httpx ni dev'dan main'ga ko'chirish (Wave 0):
uv add --project services/core-api "httpx==0.28.1"
```

**Version verification (2026-08-02 da PyPI'da va mahalliy o'rnatish bilan bajarildi):**

```bash
pip index versions arq            # 0.28.0  -> redis[hiredis]<6,>=4.2.0   ⛔ TO'QNASHUV
pip index versions taskiq         # 0.12.4  (2026-05-08, MIT)
pip index versions taskiq-redis   # 1.2.3   (2026-06-23, MIT) -> redis<9,>=8.0.0  ✅
pip index versions tenacity       # 9.1.4
pip index versions respx          # 0.23.1  (2026-04-08, BSD-3-Clause)
```

---

## Package Legitimacy Audit

`slopcheck` mahalliy muhitda mavjud va **PyPI ekotizimi aniq ko'rsatilgan holda** ishlatildi (`slopcheck install -e pypi ...`).

> ⚠ **Rejaga eslatma (2-fazadan meros):** `slopcheck` ekotizimni loyiha fayllaridan aniqlaydi va bu repoda (`package.json` ildizda) **npm** deb topadi. `-e pypi` berilmasa barcha Python paketlari soxta `[SLOP]` oladi. **Har doim `-e pypi` bering.**

| Paket | Registry | Versiya / reliz | Litsenziya | Source repo | slopcheck | Disposition |
|-------|----------|-----------------|-----------|-------------|-----------|-------------|
| `taskiq` | PyPI | 0.12.4 — 2026-05-08 | MIT | github.com/taskiq-python/taskiq | **[OK]** | ✅ Approved |
| `taskiq-redis` | PyPI | 1.2.3 — 2026-06-23 | MIT | github.com/taskiq-python/taskiq-redis | **[OK]** | ✅ Approved |
| `tenacity` | PyPI | 9.1.4 | Apache-2.0 | github.com/jd/tenacity | **[OK]** | ✅ Approved |
| `respx` | PyPI | 0.23.1 — 2026-04-08 | BSD-3-Clause | github.com/lundberg/respx | **[OK]** | ✅ Approved (dev) |
| `arq` | PyPI | 0.28.0 — 2026-04-16 | MIT | github.com/python-arq/arq | **[OK]** | ⛔ **RAD ETILDI** — legitim paket, lekin **versiya to'qnashuvi** (E.16). Bu slopcheck masalasi emas |
| `cryptography` | PyPI | 49.0.0 | Apache-2.0 / BSD | pyca/cryptography | — (allaqachon o'rnatilgan) | ✅ Mavjud |
| `httpx` | PyPI | 0.28.1 | BSD-3-Clause | encode/httpx | — (allaqachon o'rnatilgan) | ✅ Mavjud — **dev → main ga ko'chiriladi** |

**slopcheck `[SLOP]` verdikti bilan olib tashlangan paketlar:** yo'q
**Shubhali `[SUS]` deb belgilangan paketlar:** yo'q

> `taskiq` va `taskiq-redis` CLAUDE.md loyiha-darajasidagi tadqiqotida **nomma-nom** ko'rsatilgan (rasmiy manba) **va** slopcheck `[OK]` bergan **va** PyPI'da versiya/litsenziya tasdiqlangan → `[VERIFIED: PyPI registry]`. `respx` va `tenacity` — bir xil maqom.

### Konteyner image'lari

| Image | Manba | Litsenziya | Xavf |
|-------|-------|-----------|------|
| `alexxit/go2rtc:1.9.14` | Rasmiy (AlexxIT) | MIT | ⚠ **GHSA-wwww-5h25-jf98 (CVSS 9.1)** — `exec:` orqali RCE. Yumshatish D.13 da (API hech qachon ochilmaydi + `src` allow-list). Bu go2rtc'ning zaifligi emas — **uni noto'g'ri ishlatishning** natijasi |
| `linuxserver/wireguard` | linuxserver.io | GPL-2.0 | Alohida tarmoq servisi — AGPL emas |

---

## Don't Hand-Roll

| Muammo | Qurmang | O'rniga ishlating | Sabab |
|--------|---------|-------------------|-------|
| HTTP Digest **klient** tomoni | RFC 7616 hisoblagichini o'zingiz | **`httpx.DigestAuth`** | `nc`/`cnonce`/`qop`/`opaque`/`stale` va qayta-yuborish semantikasi — nozik va sinalgan |
| Simmetrik shifrlash | AES + IV + HMAC qo'lda | **`cryptography.fernet.Fernet`** | IV boshqaruvi, padding, autentifikatsiyalangan shifrlash, vaqt tamg'asi — hammasi tayyor |
| Kalit rotatsiyasi | Ikkita kalitni qo'lda sinash | **`MultiFernet` + `.rotate()`** | Rasmiy API mavjud; keyin retrofit qilish mavjud qatorlarni o'qib bo'lmas qiladi |
| Log/audit sirlarini maskalash | Yangi filtr | **`censor_secrets` (1-fazadan)** — `nvr_password`/`rtsp_password` **allaqachon ro'yxatda** | Rekursiv, ikki qatlamda (log + audit JSONB) sinovdan o'tgan |
| RTSP → WebRTC/HLS | ffmpeg quvuri, WebRTC signalling | **go2rtc** | CLAUDE.md'da qulflangan; SDP/ICE/DTLS/SRTP hand-roll qilinmaydi |
| RTSP tsiklli test manbai | Doimiy ishlaydigan ffmpeg boshqaruvchisi | **go2rtc `exec:` + `{output}`** | Jarayon hayotiy sikli, qayta ulanish, `starttimeout` — go2rtc'da |
| Fon-vazifa navbati | `SKIP LOCKED` + lease + heartbeat qo'lda (~80 qator) | **`taskiq` + `taskiq-redis`** | ⚠ Chegaraviy: bitta job turi uchun `SKIP LOCKED` himoyalanadigan tanlov. Lekin lease timeout'i, qayta urinish va o'lgan-worker aniqlash — aynan bu joyda xato qilinadi |
| Retry siyosati | `for i in range(3)` | **`tenacity`** (⚠ faqat tarmoq xatolarida) | Eksponensial backoff + jitter |
| XML parse | Regex | **`xml.etree.ElementTree`** + namespace-agnostik yordamchi | ⚠ Buzilgan NVR ham hujum manbai → **`defusedxml`** (2-fazadan mavjud) tavsiya etiladi |
| Multi-tenant izolyatsiya | `WHERE market_id = ...` intizomi | **Postgres RLS (1-faza naqshi)** | 4 ta yangi jadval `test_meta.py` invariantlaridan o'tadi |
| Idempotentlik | `SELECT` keyin `INSERT` | **`UNIQUE (market_id, nvr_id, channel_no)` + `ON CONFLICT`** | Parallel skanlarda tekshir-keyin-yoz **poyga** beradi |

**Asosiy tushuncha:** bu fazada hand-roll qilinishi kerak bo'lgan **yagona** narsa — **Digest challenge'ning SERVER tomoni** (`nvr-sim` da, ~70 qator). Buning tayyor yechimi yo'q va aynan uning **haqiqiyligi** butun SC#7 da'vosini ushlab turadi. Qolgan hamma joyda hand-roll — xato.

---

## Common Pitfalls

### Pitfall 1: `arq` ni CLAUDE.md aytgani uchun o'rnatish (VERIFIED — empirik)

**Nima bo'ladi:** `uv add arq` → `redis` 8.0.1 dan 5.x ga tushadi yoki `uv` rezolyutsiya xatosi beradi.
**Nega:** `arq 0.28.0` → `redis[hiredis]<6,>=4.2.0`; `core-api` → `redis[hiredis]==8.0.1`.
**Qanday qochish:** `taskiq` + `taskiq-redis` (E.16). CLAUDE.md ning "Version Compatibility" jadvaliga **bu qator qo'shilishi kerak**.
**Ogohlantiruvchi belgi:** `uv.lock` diff'ida `redis` versiyasining pasayishi.

### Pitfall 2: XML namespace'ni e'tiborsiz qoldirish (VERIFIED — fixture XML)

**Nima bo'ladi:** `root.find("deviceType")` → `None`. Parser jimgina bo'sh natija beradi, kashfiyot "0 kanal topildi" deydi.
**Nega:** Hikvision javoblari `xmlns="http://www.hikvision.com/ver20/XMLSchema"` bilan keladi; `ElementTree` yorliqlarni `{ns}tag` qiladi.
**Qanday qochish:** namespace-agnostik yordamchi (`tag.rpartition('}')[2]`). Unit testda **namespace bilan** XML ishlatilsin.
**Ogohlantiruvchi belgi:** "Ulanish muvaffaqiyatli, lekin 0 kanal".

### Pitfall 3: `401` da retry qilib hisobni qulflash

**Nima bo'ladi:** `tenacity` 3 marta urinadi × foydalanuvchi 2 marta bosadi = 6 urinish → **hisob 30 daqiqaga qulflanadi**. Endi **to'g'ri parol ham ishlamaydi** va admin nima bo'lganini tushunmaydi.
**Nega:** Hikvision ~5 xato urinishdan keyin qulflaydi.
**Qanday qochish:** retry **faqat** tarmoq xatolarida; `401` — hech qachon. Plyus `test-connection` endpointida **rate-limit**.
**Ogohlantiruvchi belgi:** javob tanasida `<lockStatus>locked</lockStatus>`.

### Pitfall 4: `simulator-confirms-itself`

**Nima bo'ladi:** Sim XML'i parser kutgan shaklda qo'lda yoziladi → CI yashil → real qurilmada hammasi yiqiladi.
**Nega:** Test o'z taxminini o'zi tasdiqlaydi.
**Qanday qochish:** fixture'lar **yozib olingan dump'dan** (`hikvision_next` `DS-7616NI-K2.json` / `DS-7732NI-M4.json`), manba izohi bilan; `test_sim_fixtures.py` darvozasi.
**Ogohlantiruvchi belgi:** fixture XML'ida namespace yo'q yoki maydonlar "juda toza".

### Pitfall 5: go2rtc API'sini proxy qilish → RCE (CVSS 9.1)

**Nima bo'ladi:** Foydalanuvchi `PUT /api/streams?src=exec:...` yuboradi → konteynerda root sifatida kod ijrosi.
**Nega:** go2rtc `exec:` manbasini API qatlamida filtrlamaydi (GHSA-wwww-5h25-jf98).
**Qanday qochish:** API portini (1984) **hech qachon** ochmang; `core-api` da `src` uchun `rtsp://` allow-list; Nginx'da `/api/streams|config|restart` **bloklansin**.
**Ogohlantiruvchi belgi:** nginx konfiguratsiyasida go2rtc'ga umumiy `location /go2rtc/ { proxy_pass ... }`.

### Pitfall 6: `PLATFORM_ADMIN` da `CAMERA_VIEW` yo'q — 2-faza Pitfall 6 ning takrori (VERIFIED — kod o'qildi)

**Nima bo'ladi:** Self-service qoidasi bo'yicha bozorni **platforma admini** ulaydi, lekin kameralar topilgach ularni **ko'ra olmaydi** (403).
**Nega:** `rbac.py:130-143` — `Role.PLATFORM_ADMIN` da `CAMERA_VIEW` **yo'q**; `CAMERA_MANAGE` esa **umuman mavjud emas**.
**Qanday qochish:** Wave 0 da `Permission.CAMERA_MANAGE` qo'shish + `PLATFORM_ADMIN` ga `CAMERA_VIEW`/`CAMERA_MANAGE` + `MARKET_ADMIN` ga `CAMERA_MANAGE` + `frontend/src/lib/rbac.ts` ko'zgusini sinxronlash.
**Ogohlantiruvchi belgi:** usta oxirida "kameralar topildi" ekrani bo'sh.

### Pitfall 7: `httpx` prod image'da yo'q (VERIFIED — kod o'qildi)

**Nima bo'ladi:** `uv sync --frozen --no-dev` bilan qurilgan runtime image'da `ImportError: No module named 'httpx'`.
**Nega:** `httpx==0.28.1` bugun `[dependency-groups] dev` da (`pyproject.toml:53`), lekin ISAPI klienti — ishlab chiqarish kodi.
**Qanday qochish:** Wave 0 da `[project] dependencies` ga ko'chirish.
**Ogohlantiruvchi belgi:** faqat **deploy paytida** ko'rinadi — testlar `dev` target'da ishlaydi va yashil bo'ladi.

### Pitfall 8: RTSP portini 554 deb qotirish

**Nima bo'ladi:** Kashfiyot yashil, kamera yozuvlari yaratilgan, **kadr kelmaydi**.
**Nega:** O'rnatuvchi RTSP portini o'zgartirgan (masalan 10554).
**Qanday qochish:** `/ISAPI/Security/adminAccesses` dan kashf etish; fallback ishlatilsa `rtsp_port_assumed=true` bilan belgilash va UI'da ko'rsatish.
**Ogohlantiruvchi belgi:** `rtsp_port_assumed = true` bo'lgan qatorlar.

### Pitfall 9: Shifrlangan parolni audit JSONB'ga yozish

**Nima bo'ladi:** `fn_audit_row()` `to_jsonb(NEW)` yozadi → `password_encrypted` bayti auditga tushadi. Ochiq matn emas, lekin kalit buzilganda **butun tarixiy parollar** ochiladi.
**Qanday qochish:** parolni **alohida `nvr_credentials` jadvaliga** ajratish va uni `AUDITED_TABLES` ga **qo'shmaslik** (E.15).
**Ogohlantiruvchi belgi:** `audit_log.changes` da `password_encrypted` kaliti.

### Pitfall 10: "Tunnelni o'chirib sinash" testi CI'da **yolg'on yashil**

**Nima bo'ladi:** Test "tunnel yo'q → ulanmadi" deb o'tadi. Lekin CI'da tunnel **hech qachon bo'lmagan** — test hech nima isbotlamaydi.
**Qanday qochish:** SC#5 ni uchta tekshiriladigan da'voga ajratish (C.11): xususiy-IP validatsiyasi (unit), `AllowedIPs` da `0.0.0.0/0` yo'qligi (unit), `ip route get` (deploy smoke).
**Ogohlantiruvchi belgi:** VPN testi CI'da hech qachon qizarmaydi.

### Pitfall 11: Kanal yozuvini `DELETE` qilish

**Nima bo'ladi:** Kamera vaqtincha oflayn → qayta skan uni o'chiradi → 4-fazadagi snapshotlar va 5-fazadagi zonalar **yetim** qoladi.
**Qanday qochish:** `DELETE` **hech qachon**; `status='offline'` (SC#2 ning aniq talabi).
**Ogohlantiruvchi belgi:** repozitoriyada `delete(Camera)`.

### Pitfall 12: NVR'dagi kanal nomi admin nomini bosib ketishi

**Nima bo'ladi:** Admin kamerani "Sabzavot qatori" deb nomlaydi; keyingi skan uni "Camera 03" ga qaytaradi.
**Qanday qochish:** `name_overridden` bayrog'i (A.4) — SC#2 ning "mavjudi tegilmaydi" qismi.
**Ogohlantiruvchi belgi:** `ON CONFLICT DO UPDATE SET name = EXCLUDED.name` shartsiz.

### Pitfall 13: taskiq worker'da tenant konteksti yo'q

**Nima bo'ladi:** Job DB'ga yozmoqchi bo'ladi → RLS **0 qator** beradi → job "muvaffaqiyatli" tugaydi, hech nima yozilmaydi.
**Nega:** `get_tenant_session` — HTTP dependency'si; worker'da `Request` yo'q, GUC'lar bo'sh → fail-closed.
**Qanday qochish:** job o'z sessiyasini ochib `set_tenant_context(market_id=..., actor_kind=ActorKind.SYSTEM)` chaqiradi. **Bu loyihaning birinchi fon-vazifasi** — naqsh shu yerda o'rnatiladi va 4-faza uni meros oladi.
**Ogohlantiruvchi belgi:** job `succeeded`, `channels_added = 0`.

---

## Environment Availability

| Bog'liqlik | Kim talab qiladi | Mavjud | Versiya | Fallback |
|------------|------------------|--------|---------|----------|
| Docker | compose, testcontainers, sim | ✓ | 29.4.2 | — |
| Node / npm | frontend, `package.json` yorliqlari | ✓ | v24.14.1 | — |
| Python + pip | paket tekshiruvi | ✓ | pip 25.3 | — |
| `slopcheck` | paket legitimligi | ✓ | mavjud (**`-e pypi` majburiy**) | — |
| `postgres:18.4-trixie` | RLS testlari | ✓ (1–2 fazalarda ishlatilgan) | 18.4 | — |
| `valkey:9.1.1-alpine` | taskiq brokeri + kesh | ✓ (compose'da) | 9.1.1 | — |
| **`ffmpeg` (xostda)** | sim video manbai | **✗** | — | ✅ **`alexxit/go2rtc` image'i ffmpeg'ni O'ZIDA olib keladi** — xostga o'rnatish **shart emas** |
| `alexxit/go2rtc:1.9.14` | jonli ko'rish + sim RTSP | ✗ (hali tortilmagan) | — | — (`docker pull`) |
| **Real Hikvision NVR** | yakuniy tasdiq | **✗** | — | ✅ **`nvr-sim`** — CAM-09 ning butun mavjudlik sababi |
| WireGuard kernel moduli | VPN sidecar | ✗ (Windows dev xostida) | — | ⚠ **Faqat VPS'da sinaladi**; CI'da C.11 ning konfiguratsiya testlari ishlaydi |
| `ctx7` CLI / Context7 MCP | kutubxona hujjatlari | ✗ | — | WebFetch + rasmiy docs (ishlatildi) |
| Brave / Exa / Firecrawl | qidiruv | ✗ (config: `false`) | — | Built-in WebSearch (ishlatildi) |

**Fallback'siz yetishmayotgan bog'liqliklar:** yo'q — **fazani bloklaydigan hech narsa yo'q**.

**Fallback bilan yetishmayotganlar:**

- **Real NVR** → `nvr-sim` (CAM-09). Bu fazaning **loyihalash asosi**, kamchilik emas.
- **`ffmpeg` xostda** → go2rtc konteyneri ichida. Sim uchun xost o'zgartirilmaydi.
- **WireGuard** → dev'da `vpn` profili ishga tushirilmaydi; sim compose tarmog'ida turadi, tunnel kerak emas. Bu **to'g'ri**: tunnel — deploy masalasi, ilova masalasi emas.

---

## Validation Architecture

### Test Framework

| Xususiyat | Qiymat |
|-----------|--------|
| Framework | `pytest 9.1.1` + `pytest-asyncio 1.4.0` (`asyncio_mode = "auto"`), `testcontainers 4.15.0` |
| Config fayl | `pyproject.toml` → `[tool.pytest.ini_options]`; **yangi markerlar: `sim`, `hardware`** (mavjud `tenancy` naqshi bo'yicha) |
| Baza | `postgres:18.4-trixie`, `sbozor_app` roli — SQLite **TAQIQLANGAN** |
| HTTP mock (unit) | **`respx 0.23.1`** (yangi dev-paket) |
| **E2E NVR** | **`nvr-sim` + `go2rtc-sim` konteynerlari (`--profile sim`)** |
| Frontend | `vitest 4.1.10` + `jsdom 30.0.1` |
| Quick run (unit) | `docker compose --profile test run --rm tests pytest tests/unit -x -q` |
| **Quick run (sim E2E)** | `npm run test:sim` |
| Full suite | `npm run test` + `npm run test:tenancy` + `npm run test:sim` |
| Faza darvozasi | `npm run gate` (lint + mypy + backend + tenancy + **sim** + i18n + typecheck + eslint + build) |

### Phase Requirements → Test Map

| Req / Mezon | Xulq-atvor (kuzatiladigan dalil) | Test turi | Avtomatik buyruq | Fayl bormi? |
|-------------|----------------------------------|-----------|------------------|-------------|
| **SC#7 darvozasi** | `nvr-sim` yetib boriladi; **CI'da `skip` EMAS, `fail`** | integration (sim) | `pytest tests/integration/test_nvr_discovery.py::test_sim_is_reachable -x` | ❌ Wave 0 |
| **SC#1** / CAM-08 | Faqat host+login+parol berilgan → `deviceInfo` o'qiladi, kanallar sanaladi, har biriga kamera yaratiladi (asosiy **va** sub URL) | integration (sim) | `pytest tests/integration/test_nvr_discovery.py::test_discovery_creates_cameras -x` | ❌ Wave 0 |
| SC#1 | Hosil qilingan URL **aynan** `rtsp://<host>:<port>/Streaming/Channels/{ch}01` / `{ch}02` | unit | `pytest tests/unit/test_rtsp_url.py -x` | ❌ Wave 0 |
| SC#1 / A.2 | Sim `adminAccesses` da **10554** bersa, URL 10554 bilan quriladi (554 emas) | integration (sim, `port_moved`) | `...::test_rtsp_port_is_discovered_not_assumed -x` | ❌ Wave 0 |
| SC#1 / A.1 | XML **namespace bilan** parse bo'ladi | unit (respx) | `pytest tests/unit/test_isapi_parser.py::test_namespaced_xml -x` | ❌ Wave 0 |
| SC#1 / A.1 | `deviceType=IPCamera` → standalone yo'li (`InputProxy` chaqirilmaydi) | integration (sim) | `...::test_standalone_camera_path -x` | ❌ Wave 0 |
| **SC#2** | Ikkinchi skan: `channels_added=0`, mavjud qatorlarning `id` va `first_seen_at` **o'zgarmagan** | integration (sim) | `...::test_rescan_is_idempotent -x` | ❌ Wave 0 |
| SC#2 | Sim `channel_removed:[5]` → kamera `offline`, **`DELETE` bo'lmagan** | integration (sim) | `...::test_missing_channel_goes_offline_not_deleted -x` | ❌ Wave 0 |
| SC#2 | Sim `channel_added` → yangi kamera qo'shiladi, boshqalar tegilmaydi | integration (sim) | `...::test_new_channel_is_added -x` | ❌ Wave 0 |
| SC#2 | Admin nomi o'zgartirgan kamera qayta skanda **tiklanmaydi** (`name_overridden`) | integration (sim) | `...::test_manual_name_survives_rescan -x` | ❌ Wave 0 |
| SC#2 | `camera_swapped` → `source_changed` audit qatori | integration (sim) | `...::test_camera_swap_is_audited -x` | ❌ Wave 0 |
| SC#2 (DB kafolati) | Xom `INSERT` bilan dublikat `(market_id,nvr_id,channel_no)` → **23505** | tenancy | `pytest tests/tenancy/test_camera_meta.py::test_channel_uniqueness -x` | ❌ Wave 0 |
| **SC#3** | **Har `error_code` uchun alohida test** — kod **va** foydalanuvchi matni (12 rejim, B.8) | integration (sim), parametrizatsiyalangan | `pytest tests/integration/test_nvr_errors.py -x` | ❌ Wave 0 |
| SC#3 / A.3 | `clock_drift` `401` dan **OLDIN** aniqlanadi (`Date` sarlavhasidan) | integration (sim, `clock_drift`) | `...::test_clock_drift_detected_before_auth -x` | ❌ Wave 0 |
| SC#3 / A.3 | `401` da **retry BAJARILMAYDI** (sim urinishlarni sanaydi = 1) | integration (sim, `bad_password`) | `...::test_auth_failure_is_not_retried -x` | ❌ Wave 0 |
| SC#3 / A.3 | `account_locked` → yangi urinish `unlockTime` gacha **bloklanadi** | integration (sim) | `...::test_locked_account_blocks_further_attempts -x` | ❌ Wave 0 |
| SC#3 / A.3 | `basic_only` firmware → `nvr_auth_mode_basic_only` (`digest/basic` tavsiyasi) | integration (sim) | `...::test_basic_only_firmware_is_diagnosed -x` | ❌ Wave 0 |
| SC#3 / A.5 | `stream_limit:4` → 5-chi oqim rad etiladi, `nvr_stream_limit` xabari | integration (sim) | `...::test_stream_limit_produces_actionable_error -x` | ❌ Wave 0 |
| SC#3 (i18n) | Har `error_code` uchun **uchala tilda** tarjima mavjud | unit (frontend) | `npm --prefix frontend run test -- i18n-nvr` | ❌ Wave 0 |
| **SC#4** | Bazadagi `password_encrypted` xom o'qilganda ochiq matn parol **topilmaydi** | integration | `pytest tests/integration/test_nvr_credentials.py::test_password_is_encrypted_at_rest -x` | ❌ Wave 0 |
| SC#4 | **Har bir** NVR endpointining xom javob tanasida parol satri yo'q | integration (marshrut matritsasi) | `...::test_password_never_in_any_response -x` | ❌ Wave 0 |
| SC#4 | `audit_log.changes` da parol (ochiq **yoki shifrlangan**) yo'q | integration | `...::test_password_never_in_audit -x` | ❌ Wave 0 |
| SC#4 | `structlog` chiqishida `nvr_password` → `***` | unit (**mavjud infratuzilma**) | `pytest tests/unit/test_logging.py -x` | ✅ mavjud (yangi holat qo'shiladi) |
| SC#4 | `MultiFernet` bilan eski kalitda shifrlangan qator **o'qiladi** | unit | `pytest tests/unit/test_secrets.py::test_key_rotation -x` | ❌ Wave 0 |
| **SC#5** / C.11 | Ommaviy (marshrutlanadigan) IP `host` sifatida **rad etiladi**; xususiy IP va hostname **qabul qilinadi** | unit | `pytest tests/unit/test_nvr_host_validation.py -x` | ❌ Wave 0 |
| SC#5 / C.11 | `ops/wireguard/wg0.conf` da `AllowedIPs` **`0.0.0.0/0` emas** | unit (config parse) | `pytest tests/unit/test_wireguard_config.py -x` | ❌ Wave 0 |
| SC#5 | `ip route get <nvr_ip>` → `wg0` | **manual / deploy smoke** | `ops/scripts/verify-tunnel.sh` | ❌ Wave 0 — **real infra kerak** |
| **SC#6** / CAM-03 | `CAMERA_VIEW` bo'lgan direktor jonli token oladi; **tokensiz** `/live/...` → 403 | integration | `pytest tests/integration/test_live_view.py -x` | ❌ Wave 0 |
| SC#6 | A bozori direktori B bozori kamerasiga token so'rasa → **404** | tenancy (**avtomatik**) | `pytest tests/tenancy/test_cross_tenant.py -x` | ✅ mavjud (yangi marshrutlar qo'shiladi) |
| SC#6 | Muddati o'tgan token → 403 | integration | `...::test_expired_live_token_is_rejected -x` | ❌ Wave 0 |
| SC#6 | Jonli ko'rish `audit_log` ga `reason='live_view'` yozadi; **403 olgan so'rov yozmaydi** | integration | `...::test_live_view_is_audited -x` | ❌ Wave 0 |
| **D.13 / RCE** | `src` da `exec:` / `ffmpeg:` **rad etiladi** | unit | `pytest tests/unit/test_go2rtc_client.py::test_rejects_exec_source -x` | ❌ Wave 0 |
| D.13 | Kamera kashf qilingach go2rtc'ga `PUT /api/streams` **restart'siz** qo'shiladi | integration (sim) | `pytest tests/integration/test_live_view.py::test_stream_registered_dynamically -x` | ❌ Wave 0 |
| **CAM-09 / B.9** | `services/core-api/app/` ichida `nvr-sim`/`__sim__`/`SIM_` satrlari **umuman yo'q** | unit (manba skani) | `pytest tests/unit/test_no_sim_branching.py -x` | ❌ Wave 0 |
| CAM-09 / B.7 | Har sim fixture'i XML sifatida parse bo'ladi, Hikvision namespace'iga va **manba izohiga** ega | unit | `pytest tests/unit/test_sim_fixtures.py -x` | ❌ Wave 0 |
| E.16 / Pitfall 13 | Job tenant kontekstini o'rnatadi — `channels_added > 0` | integration (sim) | `...::test_worker_sets_tenant_context -x` | ❌ Wave 0 |
| E.16 | Bir vaqtda ikkinchi skan → **409** | integration | `...::test_concurrent_discovery_is_rejected -x` | ❌ Wave 0 |
| **FOUND-02 (regressiya)** | 4 ta yangi jadvalda `market_id` + RLS ENABLE+FORCE + policy + indeks | tenancy (**mavjud, avtomatik**) | `npm run test:tenancy` | ✅ `tests/tenancy/test_meta.py` |
| Pitfall 6 | `PLATFORM_ADMIN` kamera qo'sha **va ko'ra** oladi | unit | `pytest tests/unit/test_rbac_matrix.py::test_platform_admin_can_manage_cameras -x` | ❌ Wave 0 |
| Pitfall 7 | `httpx` **runtime** bog'liqliklarida | unit | `pytest tests/unit/test_runtime_deps.py -x` | ❌ Wave 0 |
| Migratsiya butunligi | `alembic upgrade head` → autogenerate **bo'sh diff** | integration | mavjud CI qadami | ✅ mavjud |

### Uskunasiz nima **isbotlanadi**, nima **isbotlanmaydi**

> Bu bo'lim ROADMAP ning "tekshiruv simulyator ustida bajariladigan qilib loyihalanadi" qoidasining halol hisobi.

| Isbotlanadigan (sim'da, **bugun**, CI'da) | Isbotlanmaydigan (real qurilma/infra kerak) |
|-------------------------------------------|----------------------------------------------|
| Digest handshake'ning **to'liq** bajarilishi | Karmana NVR'ining **aniq firmware** xulqi |
| Kashfiyot → kamera yozuvlari yo'li | `InputProxy` javobining o'sha firmware'dagi maydonlari |
| Idempotentlik (qo'shish / offline / tegmaslik) | 25 kanalda **haqiqiy** bitreyt chegarasi (A.5) |
| 12 ta xato yo'lining har biri va **matni** | Chegaraning **RTSP javobida qanday ko'rinishi** (OQ-2) |
| Fernet shifri, javob/jurnal/audit darvozalari | Tunnel ostidagi **haqiqiy kechikish** va timeout byudjeti |
| RTSP porti kashfiyoti (554 emas) | `/picture` ning **barcha** kanallarda mavjudligi |
| go2rtc'ga dinamik ro'yxatga olish + RCE darvozasi | WebRTC UDP 8555 ning bozor NAT'i ortidan ishlashi |
| Jonli ko'rish avtorizatsiyasi va audit | WireGuard tunnelining haqiqiy marshrutlanishi |
| Tenant izolyatsiyasi (4 jadval) | CGNAT ostidagi `PersistentKeepalive` barqarorligi |

### Real qurilma kelganda: **bloklamaydigan** ikkinchi to'plam

ROADMAP "tashqi bog'liqlik hech qachon `Blocks:` bo'lmaydi" deydi. Shuning uchun ikkinchi to'plam **alohida marker ostida** yoziladi va **CI'da o'tkazib yuboriladi**:

```python
# pyproject.toml: markers = ["tenancy", "sim", "hardware"]
@pytest.mark.hardware        # CI: `-m "not hardware"`;  dala: `-m hardware`
def test_real_nvr_channel_enumeration(real_nvr_url): ...
```

`ops/scripts/verify-real-nvr.sh` — bir martalik dala skripti: `deviceInfo`, `InputProxy/channels`, `adminAccesses`, har kanaldan bitta kadr, 3 ta bir vaqtdagi oqim. Chiqishi **JSON** va u sim fixture'lari bilan **solishtiriladi** — farqlar aynan Pitfall 4 ni yopadi.

> **Faza yopilishi uchun `hardware` markeri TALAB QILINMAYDI.** SC#7 aynan shuni aytadi.

### Sampling Rate

- **Har task commit'ida:** `pytest tests/unit -x -q` + o'zgargan modulning integration fayli
- **Har to'lqin birlashuvida:** `npm run test` + `npm run test:tenancy` + `npm run test:sim` + `npm --prefix frontend test`
- **Faza darvozasi:** `npm run gate` to'liq yashil (`test:sim` ichida), so'ng `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `services/core-api/pyproject.toml` — `httpx` **dev → main**; `taskiq`, `taskiq-redis`, `tenacity` qo'shish; `respx` dev'ga — **Pitfall 1, Pitfall 7**
- [ ] `services/core-api/app/security/rbac.py` — `Permission.CAMERA_MANAGE` (yangi) + `PLATFORM_ADMIN` ga `CAMERA_VIEW`/`CAMERA_MANAGE` + `MARKET_ADMIN` ga `CAMERA_MANAGE` — **Pitfall 6**
- [ ] `frontend/src/lib/rbac.ts` — RBAC ko'zgusini qo'lda sinxronlash (`rbac.py` docstring talabi)
- [ ] `app/settings.py` — `nvr_credential_key` + `nvr_credential_keys_retired` + `field_validator`; `.env.example` ga kalit **nomlari**
- [ ] `packages/sbozor-core/sbozor_core/schema_contract.py` — `AUDITED_TABLES += {nvr_devices, cameras}`; `nvr_credentials` **QO'SHILMAYDI**; `FINANCIAL_TABLES` **o'zgarmaydi**
- [ ] `migrations/entities/__init__.py` — `TENANT_TABLES += {nvr_devices, nvr_credentials, cameras, nvr_discovery_runs}`
- [ ] `pyproject.toml` — `markers` ga `sim` va `hardware`
- [ ] `compose.yaml` — `sim` profili (`nvr-sim`, `go2rtc-sim`), `worker` konteyneri, `vpn` profili; `tests` ga `NVR_SIM_BASE_URL`
- [ ] `package.json` — `test:sim` yorlig'i; `gate` ga qo'shish
- [ ] `services/nvr-sim/` — FastAPI ilovasi, Digest server, `/__sim__/` control-plane, **yozib olingan** fixture'lar
- [ ] `ops/go2rtc/go2rtc.sim.yaml` + `ops/go2rtc/go2rtc.yaml` (prod)
- [ ] `ops/nginx/nginx.conf` — `/live/` uchun `auth_request`; go2rtc `/api/streams|config|restart` **bloki** — **Pitfall 5**
- [ ] `ops/wireguard/wg0.conf.example` + `ops/scripts/verify-tunnel.sh`
- [ ] `tests/fixtures/nvr.py` — sim rejimini o'rnatuvchi fixture (`sim_mode("clock_drift", drift_seconds=420)`)
- [ ] `tests/tenancy/test_route_coverage.py` — yangi marshrutlarni qamrovga qo'shish (aks holda CI **ataylab** qizaradi)
- [ ] Framework o'rnatish: **kerak emas** — barcha vositalar 1–2 fazalardan mavjud

---

## Security Domain

**ASVS darajasi:** L1 (`.planning/config.json` → `security_asvs_level: 1`, `security_block_on: "high"`)

### Applicable ASVS Categories

| ASVS toifasi | Qo'llanadimi | Standart nazorat (bu fazada) |
|--------------|--------------|------------------------------|
| V2 Authentication | qisman | 1-fazadan o'zgarishsiz. **Yangi yuza:** NVR'ga **chiquvchi** Digest auth (`httpx.DigestAuth`) |
| V3 Session Management | **ha** | **Jonli ko'rish tokeni** — qisqa muddatli (≤60 s), imzolangan, bir kameraga bog'langan (D.13) |
| **V4 Access Control** | **ha** | RLS ENABLE+FORCE (4 jadval) · `require_permission(CAMERA_VIEW/CAMERA_MANAGE)` · Nginx `auth_request` · cross-tenant → **404** |
| **V5 Input Validation** | **ha** | `host` — **ommaviy IP rad etiladi** (C.11) · go2rtc `src` — **`rtsp://` allow-list** (D.13) · NVR XML'i — `defusedxml` |
| **V6 Cryptography** | **ha** | **Fernet / MultiFernet** (`cryptography` 49.0.0) — hand-roll **YO'Q**; kalit muhitda, **DB'da emas** |
| V7 Error Handling & Logging | **ha** | 12 ta `error_code` — foydalanuvchiga **kod**, jurnalga **tafsilot**. `censor_secrets` + `mask_sensitive` |
| **V8 Data Protection** | **ha** | NVR parollari — shifrlangan, alohida jadval, auditdan tashqarida. **Jonli tasvir = shaxsiy ma'lumot** → ko'rish auditga tushadi |
| V9 Communications | **ha** | **WireGuard split-tunnel** — NVR internetga ochilmaydi (C.11). ISAPI HTTPS ixtiyoriy (tunnel ichida) |
| V13 API | ha | `202 Accepted` + poll; aniq pydantic modellari; **javob modelida parol maydoni YO'Q** |
| V14 Configuration | **ha** | `sim` profili prodga chiqmaydi · go2rtc API porti ochilmaydi · sirlar `.env` da · `SYS_MODULE` imtiyozini kamaytirish |

### Known Threat Patterns for {FastAPI + Hikvision ISAPI + go2rtc + WireGuard}

| Naqsh | STRIDE | Standart mitigatsiya |
|-------|--------|----------------------|
| **go2rtc `exec:` orqali RCE** (CVSS 9.1) | **Elevation / Tampering** | API porti ochilmaydi · `src` `rtsp://` allow-list · Nginx bloki (D.13, Pitfall 5) [CITED: GHSA-wwww-5h25-jf98] |
| Bazaga kirgan hujumchi NVR parolini o'qishi | Information Disclosure | Fernet, kalit **ilova muhitida** (SC#4) |
| Parolning API javobida sizishi | Information Disclosure | Javob modelida **maydon yo'q** + marshrut matritsasi testi |
| Parolning jurnal/Sentry'ga sizishi | Information Disclosure | `censor_secrets` — `nvr_password`/`rtsp_password` **allaqachon ro'yxatda** |
| Parolning audit JSONB'ga sizishi | Information Disclosure | `nvr_credentials` **alohida jadval**, auditdan tashqarida (Pitfall 9) |
| **`test-connection` ni NVR'ga brute-force sifatida ishlatish** | Elevation / DoS | Rate-limit (1-fazadagi `ratelimit.py`) + `401` da retry **yo'q** + `account_locked` da bloklash (A.3) |
| **A bozori direktori B bozori kamerasini ko'rishi** | Information Disclosure | RLS + `auth_request` da `camera_id → market_id` tekshiruvi + `test_cross_tenant.py` |
| **Jonli ko'rish havolasini ulashish** | Information Disclosure | Token ≤60 s, imzolangan, `user_id` ga bog'langan |
| Oqim nomidan bozor tuzilmasini bilish | Information Disclosure | `cam_<uuid4>` — ma'nosiz nom (D.13) |
| **To'liq tunnel (`AllowedIPs=0.0.0.0/0`)** VPS trafigini bozor DSL'iga yo'naltirishi | DoS | Split-tunnel majburiy + **config testi** (C.11) |
| Buzilgan bozor qurilmasi tunnel orqali VPS'ga hujum qilishi | Elevation | WireGuard **kripto-marshrutlash**: peer'dan faqat `AllowedIPs` manbalari qabul qilinadi |
| NVR internetdan ochilishi | Elevation | Port-forward **taqiqlanadi**; `host` ommaviy IP bo'lsa **rad etiladi** |
| Buzilgan NVR'dan **XML bomba** | DoS | `defusedxml` + javob hajmi chegarasi + `httpx` timeout |
| **`401` retry hisobni qulflab tizimni yiqitishi** | DoS (o'z-o'ziga) | Retry siyosati (A.3, Pitfall 3) |
| NVR'ga 25 oqim ochib **bozor kuzatuvini yiqitish** | DoS (mijozga) | Sub-oqim standarti + go2rtc lazy + 4-fazada stagger (A.5, D.14) |
| **Sim'ning prodga chiqishi** | Tampering | `profiles: ["sim"]` + `test_no_sim_branching.py` |
| Kamera yozuvini o'chirib dalilni yo'qotish | Repudiation | `DELETE` yo'q — `status='offline'` (Pitfall 11) |
| Kashfiyotni izsiz ishga tushirish | Repudiation | `nvr_discovery_runs.triggered_by` + audit |
| Xom SQL bilan NVR manzilini o'zgartirish | Tampering | `fn_audit_row()` **DB triggeri** (D-10) |

---

## Scope Fence — bu fazada QURILMAYDIGAN narsalar

| Narsa | Qaysi faza | Bu fazada nima qilinadi (arzon ilgak) |
|-------|-----------|----------------------------------------|
| Snapshot jadvali, mavsumiy profil | 4-faza | **Hech narsa** |
| Rejalashtirilgan kadr olish, idempotentlik, retry | 4-faza | Faqat **naqsh**: navbat + tenant konteksti (E.16) 4-faza uchun o'rnatiladi |
| Sifat filtri, `light_mode` | 4-faza | Hech narsa |
| S3 / SeaweedFS arxivi | 4-faza | Hech narsa |
| Telegram alertlar (FOUND-06) | 4-faza | `nvr_discovery_runs.error_code` — alert manbai **tayyor** |
| ISAPI `/picture` **kadr olish yo'li sifatida** | 4-faza | Sim uni **qo'llaydi** va ulanish testida bir marta chaqiriladi — 4-faza ilgagi |
| ffmpeg oxirgi-chora kadr olish | 4-faza | Hech narsa |
| Kamera-zona poligonlari | 5-faza | **Faqat `cameras.id` barqarorligi** — allaqachon qilinadi (`DELETE` yo'q) |
| CV, RF-DETR, occupancy | 5-faza | Hech narsa |
| PTZ boshqaruvi | Qurilmaydi (v2) | Hech narsa |
| Kamera hodisalari (`alertStream`, motion) | Qurilmaydi (v2) | Hech narsa |
| ONVIF auto-discovery (noma'lum brendlar) | v2 | Kashfiyot **interfeys ortida** yoziladi (`DeviceProbe`) — ikkinchi brend qo'shish yangi implementatsiya bo'ladi |
| Dahua / boshqa brendlar | v2 | Xuddi shu interfeys |
| Bir nechta NVR bitta bozorda | Sxema qo'llaydi | `nvr_devices` — `market_id` bo'yicha **ko'plik**; UI'da MVP'da bitta |
| Jonli tasvirni **yozib olish** | Qurilmaydi | Hech narsa |
| WireGuard peer'larini **UI'dan** boshqarish | v2 | `wg0.conf` — ops fayli; `tunnel_subnet` maydoni **ilgak** sifatida |
| Kamera thumbnail'i ro'yxatda | 4-faza | Hech narsa |

**Erta optimizatsiya deb baholangan va QILINMAYDIGAN "ilgaklar":**

- Kamera uchun `resolution` / `codec` ustunlari — `Streaming/channels` beradi, lekin 4-fazagacha ishlatilmaydi
- NVR uchun `capabilities` JSONB keshi — kerak bo'lganda qayta so'raladi
- Jonli ko'rish uchun WebRTC TURN serveri — bozor NAT'i muammo bergandagina
- Kamera guruhlash / teglar — 5-faza zonalari bu ehtiyojni yopadi

---

## Assumptions Log

| # | Da'vo | Bo'lim | Xavf (noto'g'ri bo'lsa) | Qanday yopiladi |
|---|-------|--------|-------------------------|-----------------|
| **A1** | Hikvision hisobni **~5 xato urinishdan keyin 30 daqiqaga** qulflaydi | A.3 | Retry siyosati juda ehtiyotkor yoki juda dadil; dala testida hisob qulflanadi | Sim shu qiymatda modellashtiriladi; **real qurilmada birinchi kunda** tekshiriladi. ⚠ Chegara **sozlanadigan** bo'lsin |
| **A2** | Digest soat farqi tolerantligi — **5 daqiqa** | A.3 | Soxta `nvr_clock_drift` yoki o'tkazib yuborilgan drift | `NVR_CLOCK_DRIFT_TOLERANCE_SECONDS` **sozlama** (standart 300) |
| **A3** | `InputProxyChannel` maydonlari: `id`, `name`, `sourceInputPortDescriptor{ipAddress, srcInputPort, managePortNo, proxyProtocol, streamType}` | A.1 | Parser real javobda maydon topmaydi | Fixture **haqiqiy dump'dan** (B.7); parser yetishmagan maydonda **yiqilmaydi**, `NULL` qo'yadi |
| **A4** | 25 kanalli NVR **asosiy** oqimlarni bir vaqtda ko'tarolmaydi (bitreyt) | A.5 | Sub-oqim majburlash keraksiz ehtiyotkorlik bo'lardi | Sub/asosiy tanlovi **kamera bo'yicha sozlanadi**; standart — sub |
| **A5** | `nvr_stream_limit` heuristikasi (bitta ulanadi, N-chi uziladi) ishonchli | A.5 | Xato xabari noto'g'ri sabab ko'rsatadi | Xabar "**ehtimol**" tarzida; `error_detail` da xom javob. OQ-2 |
| **A6** | Karmana NVR'i **Hikvision** va ISAPI'ni qo'llaydi | butun faza | Butun kashfiyot yo'li boshqa brend uchun qayta yozilardi | `DeviceProbe` interfeysi ortida (Scope Fence). ⚠ **Buyurtmachidan tasdiq** — OQ-1 |
| **A7** | Bozor tomonida WireGuard qurilmasi (mini-PC/OpenWrt) **bo'ladi** | C.12 | CGNAT yechimi ishlamaydi | ROADMAP Phase 0 SC#2 buni allaqachon o'lchamoqda; **bloklamaydi** (sim bilan ishlanadi) |
| **A8** | `linuxserver/wireguard` Contabo yadrosida ishlaydi | C.11 | Userspace `wireguard-go` ga tushish (sekinroq, lekin **ishlaydi**) | Deploy smoke-testi |
| **A9** | go2rtc `PUT /api/streams` **xotirada** qo'shadi (restart'da yo'qoladi) | D.13 | Agar u avtomatik saqlansa — lazy ro'yxatga olish keraksiz ish qilardi | Lazy naqsh **ikkala holatda ham to'g'ri** — risk past |
| **A10** | `taskiq` abstraksiyasi bitta job turi uchun **ortiqcha emas** | E.16 | Ortiqcha murakkablik | Job **kutubxonadan mustaqil** sof funksiya sifatida yoziladi → ko'chirish ~10 qator |
| **A11** | RTSP shabloni `/Streaming/Channels/{ch}0{s}` Karmana firmware'ida ishlaydi | A.2 | URL noto'g'ri → kadr yo'q | Shablon **sozlama** (`rtsp_path_template`); eski `/h264/ch{n}/main/av_stream` fallback hujjatlashtiriladi |

---

## Open Questions (RESOLVED)

> **Har biri uchun taklif qilingan standart qiymat bor — rejalashtirish hech qachon javob kutib to'xtamaydi.**
>
> ✅ **Yettalasi ham 2026-08-03 da `03-CONTEXT.md` da hal qilindi** — har biri taklif qilingan standart qiymatda qulflandi:
> OQ-1 → **D-04** · OQ-2 → **D-05** · OQ-3 → **D-06** · OQ-4 → **D-07** · OQ-5 → **D-08** · OQ-6 → **D-09** · OQ-7 → **D-10**.
> Quyidagi bandlar **tarixiy asoslash** sifatida saqlanadi: ular qaror qanday qabul qilinganini va qaysi muqobil rad etilganini ko'rsatadi.

### OQ-1 — Karmana NVR'i haqiqatan Hikvision-mi va model qaysi?

- **Ma'lum:** ROADMAP va CLAUDE.md Hikvision deb yozadi; Phase 0 SC#2 "login/parol topshirilgan" ni o'lchayapti.
- **Noaniq:** Aniq model, firmware, kanallar soni.
- **Taklif qilingan standart:** `DS-7616NI-K2` (16 kanal, `V4.74.210`) va `DS-7732NI-M4` (32 kanal) fixture'lari bilan ishlash; sim standarti **6 kanal**, stress rejimi **25 kanal**. Kod `deviceType`/`model` ga qarab **tarmoqlanadi**, qotib qolmaydi.
- **Ta'sir:** Past — model tafsiloti kashfiyot mantiqini o'zgartirmaydi.

### OQ-2 — Sessiya/bitreyt chegarasi RTSP javobida qanday ko'rinadi?

- **Ma'lum:** Chegara bor (128 ulanish; amalda bitreyt); web-UI "Maximum number of streams" ko'rsatadi.
- **Noaniq:** RTSP darajasida `453`/`503` keladimi yoki ulanish **jimgina** uziladimi.
- **Taklif qilingan standart:** **Ikkala** stsenariyni sim'da modellashtirish; xabar "**ehtimol** sessiya limitiga yetildi" + `error_detail` da xom javob. Heuristika **sozlanadigan**.
- **Ta'sir:** O'rta — xato xabarining aniqligiga ta'sir qiladi, oqimga emas.

### OQ-3 — Navbat mexanizmi: 3-faza `taskiq`, 4-faza nima?

- **Ma'lum:** `arq` **bloklangan** (redis to'qnashuvi, tasdiqlangan). ROADMAP Phase 4 mexanizmni ochiq qoldirgan.
- **Noaniq:** 4-faza `taskiq` ni oladimi yoki `SKIP LOCKED` ni.
- **Taklif qilingan standart:** 3-faza **`taskiq`** ni oladi, **lekin** job sof `async def` funksiya sifatida yoziladi va taskiq dekoratori — yupqa qobiq. 4-faza boshqa yo'lni tanlasa ko'chirish ~10 qator. **Ikki mexanizm bir vaqtda saqlanmaydi.**
- **Ta'sir:** O'rta — arxitektura qarori, lekin **teskariga qaytariladigan**.

### OQ-4 — Bir nechta bozorda NVR subneti to'qnashsa?

- **Ma'lum:** Ko'p tarmoq `192.168.1.0/24` ishlatadi. Ikkinchi bozor qo'shilganda VPS marshrut jadvali chalkashadi.
- **Noaniq:** Karmanadan keyin qachon ikkinchi bozor keladi.
- **Taklif qilingan standart:** `nvr_devices.tunnel_subnet` (`cidr`) maydoni **hozirdan** + **global noyoblik tekshiruvi** (bozorlar aro). To'qnashuvda onboarding'da **aniq xato**. `1:1 NAT` yechimi hujjatlashtiriladi, **implement qilinmaydi**.
- **Ta'sir:** Past bugun, **yuqori** ikkinchi bozorda — shuning uchun arzon ilgak hozir.

### OQ-5 — Jonli ko'rish tokeni: JWT-mi yoki opaque?

- **Ma'lum:** Token qisqa muddatli va imzolangan bo'lishi kerak (SC#6). `PyJWT` allaqachon bor.
- **Noaniq:** JWT (stateless, bekor qilib bo'lmaydi) vs Valkey'dagi opaque token (bekor qilinadi, bitta so'rov qo'shadi).
- **Taklif qilingan standart:** **Qisqa muddatli JWT** (`aud="live"`, `exp<=60s`, `camera_id`+`market_id`+`user_id`). 60 soniya — bekor qilish keraksiz bo'ladigan darajada qisqa; mavjud `tokens.py` infratuzilmasi qayta ishlatiladi.
- **Ta'sir:** Past — ikkalasi ham SC#6 ni qondiradi.

### OQ-6 — Sim'ning standart kanallar soni CI'da nechta?

- **Ma'lum:** Karmana ~20–25 kanal; CI mashinasi cheklangan.
- **Taklif qilingan standart:** CI standarti **6 kanal** (tez, `DS-7616NI-K2` fixture'iga mos); **25 kanal** alohida sekin test (`-m slow`, kechalik CI). `stream_limit` testi **4** bilan.
- **Ta'sir:** Past.

### OQ-7 — Kamerani admin **o'chira** oladimi?

- **Ma'lum:** Qayta skan hech qachon `DELETE` qilmaydi (Pitfall 11). Lekin admin noto'g'ri NVR qo'shsa?
- **Taklif qilingan standart:** **Soft-delete** (`is_archived`) — yozuv qoladi, ro'yxatlardan yo'qoladi, snapshot/zona bog'lanishlari saqlanadi. Qattiq `DELETE` — **hech qachon**. Arxivlangan kanal qayta skanda **tiklanmaydi** (`is_archived` `name_overridden` kabi ishlaydi).
- **Ta'sir:** O'rta — UI va sxemaga tegadi, shuning uchun **hozir** hal qilinsin.

---

## Sources

### Primary (HIGH confidence — o'zim o'lchadim yoki rasmiy/yozib olingan manba)

- **Mahalliy paket rezolyutsiyasi** (2026-08-02): `pip install arq` → `redis 8.0.0` **uninstall** → `redis 5.3.1`; `importlib.metadata`: `arq 0.28.0 → redis[hiredis]<6,>=4.2.0`. **Bu fazaning eng muhim topilmasi** (E.16, Pitfall 1)
- **PyPI JSON API** (2026-08-02): `taskiq 0.12.4` (2026-05-08, MIT) · `taskiq-redis 1.2.3` (2026-06-23, MIT, **`redis<9,>=8.0.0`**) · `tenacity 9.1.4` (Apache-2.0) · `respx 0.23.1` (2026-04-08, BSD-3) · `arq 0.28.0` (2026-04-16, MIT)
- **`slopcheck install -e pypi`** (2026-08-02): `taskiq`, `taskiq-redis`, `tenacity`, `respx`, `arq` — **hammasi `[OK]`**
- **github.com/maciej-or/hikvision_next** — `tests/fixtures/devices/DS-7616NI-K2.json`, `DS-7732NI-M4.json`: **real qurilmalardan yozib olingan** ISAPI javoblari. `System/deviceInfo` XML'i **verbatim** olindi; endpoint ro'yxati tasdiqlandi (`System/capabilities`, `System/Video/inputs/channels`, `ContentMgmt/InputProxy/channels`, `Security/adminAccesses`, `Streaming/channels/101…602`)
- **github.com/uchkunr/hikvision-best-practices** — ISAPI endpoint reyestri; Digest oqimi (HA1/HA2/nc/cnonce); **soat farqi >5 daq**; **hisob qulflanishi ~5 urinish / 30 daq** (`<lockStatus>`/`<unlockTime>`); kanal raqamlash `{channel}{stream}`; RTSP shabloni
- **github.com/eu-evops/homebridge-hikvision** (`src/HikvisionApi.ts`) — `ContentMgmt/InputProxy/channels` + `.../status` juftligi, `id` bo'yicha birlashtirish, `online === 'true'` filtri, Digest auth
- **GHSA-wwww-5h25-jf98** (Frigate xavfsizlik ogohnomasi) — **CVSS 9.1 Critical**, go2rtc `exec:` orqali RCE, `is_restricted_source()` yumshatishi. **D.13 va Pitfall 5 ning asosi**
- **supportusa.hikvision.com** — "maximum number of streams" (128 remote connection; *"Remote connections and bandwidth are not the same concept"*); "Can I view more than 16 cameras on Hik-Connect"
- **go2rtc.org/internal/mjpeg/** — `/api/frame.jpeg` parametrlari (`src`, `w`/`width`, `h`/`height`, `rotate`, `hw`/`hardware`, `cache`) va kesh xulqi
- **go2rtc.org/internal/ffmpeg/** — `ffmpeg:{input}#{param}` sintaksisi; `raw=`, `input=`, `rotate=`, `width/height`. **Tsikl hujjatlashtirilmagan** → `exec:` tanlandi
- **deepwiki AlexxIT/go2rtc — "FFmpeg and Exec Sources"** — `exec:` `{output}` mexanikasi: MD5 yo'li, `ANNOUNCE` kutish, `starttimeout` 30 s
- **AlexxIT/go2rtc issue #1151, #1592** — `PUT /api/streams?name=&src=`, `PATCH`, `DELETE /api/streams?src=`
- **Kod bazasi** (o'qildi): `services/core-api/pyproject.toml` (`cryptography==49.0.0`, `httpx` **dev'da**, `redis==8.0.1`) · `packages/sbozor-core/sbozor_core/logging.py:36-63` (`nvr_password`/`rtsp_password` **allaqachon** `SENSITIVE_KEYS` da) · `services/core-api/app/security/rbac.py:117,130-177` (`CAMERA_VIEW` bor, `PLATFORM_ADMIN` da **yo'q**, `CAMERA_MANAGE` **umuman yo'q**) · `app/deps.py` (tenant sessiyasi, `set_tenant_context`, `ActorKind`) · `app/settings.py` (`field_validator` naqshi) · `compose.yaml` (profillar, `--workers 1`)
- **Mahalliy muhit** (2026-08-02): Docker 29.4.2 · Node v24.14.1 · pip 25.3 · `slopcheck` mavjud · **`ffmpeg` xostda YO'Q**

### Secondary (MEDIUM confidence — tekshirilgan qidiruv natijasi)

- **Hikvision IP Surveillance API (RaCM Part) User Guide v2.0** — *"NVRs and hybrid DVRs support external IP network devices as their input sources"*; DVR vs NVR "channel" semantikasi farqi
- **Hikvision IP Surveillance API User Guide v2.6** — `Security/adminAccesses` → `AdminAccessProtocolList` (`protocol`, `portNo`; HTTP 80 / HTTPS 443 / DEV_MANAGE 8000 / RTSP 554)
- **pkg.go.dev/github.com/tangtang666/hikvision-sdk** — `InputProxyChannelList` / `InputProxyChannel` / `sourceInputPortDescriptor` maydonlari (`ipAddress`, `srcInputPort`, `managePortNo`, `proxyProtocol`, `streamType`)
- **bluenviron/mediamtx** hujjatlari — `ffmpeg -re -stream_loop -1 -i file.mp4 -f rtsp ...` naqshi (go2rtc `exec:` uchun bir xil ffmpeg argumentlari)

### Negative findings (VERIFIED — mavjud emasligi tasdiqlandi)

- **Tayyor Hikvision NVR emulyatori / ISAPI mock serveri YO'Q.** Ikki mustaqil qidiruv (GitHub topics `hikvision`, `isapi`, `hikvision-isapi`, `hikvision-camera` + maqsadli "mock/simulator/emulator") **faqat klientlarni** topdi. Bu B.6 dagi "qo'lda quriladi" qarorining asosi

### Tertiary (LOW confidence — tasdiq talab qiladi)

- Sessiya/bitreyt chegarasining **RTSP javobida qanday ko'rinishi** — to'g'ridan-to'g'ri manba topilmadi → **OQ-2**, sim'da ikki variant
- NVR chiquvchi bitreyt byudjetining aniq qiymati (~32–256 Mbps) — model spetsifikatsiyalaridan **umumlashtirilgan** → **A4**
- Karmana NVR'ining brendi/modeli — hujjatdan, o'lchanmagan → **A6 / OQ-1**

---

## Metadata

**Confidence breakdown:**

| Soha | Daraja | Sabab |
|------|--------|-------|
| Paket versiyalari va `arq` to'qnashuvi | **HIGH** | Mahalliy o'rnatish bilan **empirik reproduktsiya** + `importlib.metadata` + PyPI `requires_dist` |
| 1-fazadan meros aktivlar va bo'shliqlar | **HIGH** | Kod fayl-fayl o'qildi (`logging.py`, `rbac.py`, `deps.py`, `pyproject.toml`, `compose.yaml`) |
| ISAPI endpoint yo'llari va `deviceInfo` XML'i | **HIGH** | **Real qurilmadan yozib olingan** fixture (`hikvision_next`) + uch mustaqil manba mos keladi |
| go2rtc RCE zaifligi va yumshatilishi | **HIGH** | Rasmiy GitHub xavfsizlik ogohnomasi, CVSS bilan |
| go2rtc API va `exec:`/`{output}` mexanikasi | **HIGH** | Rasmiy hujjat + deepwiki manba tahlili + issue tracker |
| Digest mexanikasi va xato taksonomiyasi | **MEDIUM-HIGH** | RFC + ishonchli integratsiya qo'llanmasi; **aniq chegaralar (5 urinish / 5 daqiqa) bitta manbadan** → A1/A2 |
| `InputProxy` javobining aniq maydonlari | **MEDIUM** | Uch manba mos keladi, lekin verbatim XML to'liq o'qilmadi → **B.7 fixture qoidasi bu bo'shliqni yopadi** |
| Simulyator arxitekturasi | **MEDIUM-HIGH** | Tayyor yechim yo'qligi **tasdiqlangan**; tanlangan yo'l mavjud stek ustida quriladi; hali qurilmagan |
| WireGuard topologiyasi va CGNAT | **MEDIUM-HIGH** | Standart, yaxshi hujjatlashtirilgan naqsh; **bu muhitda o'lchanmagan** |
| Sessiya/bitreyt chegarasi | **MEDIUM** | Rasmiy support maqolasi mavjud, lekin model bo'yicha o'zgaradi |
| Chegaraning RTSP javobida ko'rinishi | **LOW** | Manba yo'q → OQ-2, sim'da ikki variant |
| Karmana qurilmasining aniq xulqi | **LOW** | O'lchanmagan va **bu fazada o'lchanmaydi** — ROADMAP shunday loyihalagan |

**Research date:** 2026-08-02
**Valid until:** 2026-09-01 (30 kun). Ertaroq qayta ko'rish sharti: go2rtc yangi major reliz chiqarsa (RCE yumshatilishi o'zgarishi mumkin) yoki 4-faza navbat mexanizmini `taskiq` dan boshqasiga hal qilsa (OQ-3).
