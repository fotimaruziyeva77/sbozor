# WireGuard — VPS ↔ bozor tunneli (CAM-02, SC#5)

NVR internetga **hech qachon** ochilmaydi. VPS unga **faqat** WireGuard
tunneli orqali boradi va bu fazadagi butun tarmoq qarori shu jumladan
kelib chiqadi.

```
┌─ Contabo VPS ────────────────────────────────┐        ┌─ Karmana bozori ──────────┐
│  wg0: 10.10.0.1/24                           │        │  Mini-PC / OpenWrt        │
│   AllowedIPs = 10.10.0.2/32, 192.168.1.0/24  │◄───────┤  wg0: 10.10.0.2/24        │
│                ▲                             │  UDP   │  AllowedIPs = 10.10.0.1/32│
│                └── FAQAT shu ikkisi.         │ 51820  │  PersistentKeepalive = 25 │
│                    0.0.0.0/0 HECH QACHON     │        │  Endpoint = vps:51820     │
│                                              │        │            │              │
│  go2rtc (RTSP→WebRTC)   core-api (ISAPI)     │        │            ▼              │
└──────────────────────────────────────────────┘        │  NVR 192.168.1.64:80/554  │
                                                        │  (internetga OCHIQ EMAS)  │
                                                        └───────────────────────────┘
```

---

## 1. Nega split-tunnel — `AllowedIPs` ning **ikki vazifasi**

Bu WireGuard'dagi eng ko'p chalkashtiradigan joy: bitta direktiva **ikki
mustaqil ishni** bajaradi.

| Vazifa | Yo'nalish | Ma'nosi |
|--------|-----------|---------|
| **Marshrutlash** | chiqishda | Bu manzillarga ketayotgan trafik **shu peer'ga** yuboriladi |
| **Kripto-marshrutlash** | kirishda | Bu peer'dan **faqat shu manzillardan** kelgan paket qabul qilinadi; qolgani **jimgina tashlanadi** |

Ikkinchisi bizning **xavfsizlik da'vomiz**: bozor tomonidagi qurilma
buzilsa ham, u tunneldan `192.168.1.0/24` dan tashqari manba manzili
bilan paket **yubora olmaydi** — VPS ularni kripto-marshrutlash
bosqichida tashlaydi (T-03-52).

### `0.0.0.0/0` nima qiladi

VPS peer'ida `AllowedIPs = 0.0.0.0/0` yozilsa, marshrutlash vazifasi
**butun internetni** shu peer ortiga qo'yadi:

- VPS'ning Telegram'ga chiqishi bozor DSL'idan o'tadi;
- Let's Encrypt yangilanishi bozor DSL'idan o'tadi va sertifikat
  muddati tugaganda platforma **HTTPS'siz** qoladi;
- foydalanuvchilarga qaytadigan javoblar ham o'sha kanaldan ketadi.

Ya'ni bitta satr **butun platformani** bozorning uy internetiga bog'lab
qo'yadi. Shuning uchun qoida **CI'da o'lchanadi**:
`tests/unit/test_wireguard_config.py` `wg0.conf.example` ni **va shu
faylning §2 dagi `ini` blokini** parse qiladi.

---

## 2. CGNAT — bozor tomoni «rozetkaga ulaydi» (D-14)

CGNAT'da bozorning ommaviy IP'si **yo'q** va unga tashqaridan ulanib
bo'lmaydi. Lekin WireGuard **peer-to-peer**, klient-server emas: bozor
tomoni **birinchi** paketni yuborsa, NAT jadvalida yo'l ochiladi va VPS
o'sha yo'l orqali javob bera oladi.

`PersistentKeepalive = 25` har 25 soniyada bo'sh paket yuboradi va NAT
yozuvini tirik saqlaydi (odatiy NAT timeout'i 30–120 s). **Bu CGNAT'ni
yengadigan yagona qator.**

> ⚠ Shuning uchun **VPS peer'ida `Endpoint` yozilmaydi**: bozorning
> manzili o'zgaruvchan va VPS uni handshake'dan **o'rganadi**.

**Bozor tomonidagi qurilmaning konfiguratsiyasi** (jo'natishdan **oldin**
yoziladi):

```ini
[Interface]
PrivateKey = <karmana-qurilmasining-maxfiy-kaliti>
Address    = 10.10.0.2/24

[Peer]
PublicKey           = <VPS-ochiq-kaliti>
Endpoint            = vps.sbozor.uz:51820
# FAQAT VPS. `0.0.0.0/0` bo'lsa bozorning butun trafigi tunneldan
# o'tardi — bozor internetini VPS kanaliga bog'lab qo'yardi.
AllowedIPs          = 10.10.0.1/32
PersistentKeepalive = 25
```

### On-site odam nima qiladi

| Qadam | Kim |
|-------|-----|
| 1. Qurilmani rozetkaga ulash | On-site (har kim) |
| 2. Ethernet kabelini NVR bilan bir tarmoqqa ulash | On-site |
| 3. (hammasi) | — |

Kalitlar, `wg0.conf` va NVR subneti **jo'natishdan oldin** yoziladi. Bu
ROADMAP ning «muhandis aralashuvi qabul qilinmaydi» qoidasining tarmoq
tomonidagi ifodasi.

---

## 3. Subnet to'qnashuvi (D-07)

Ikkala bozor ham `192.168.1.0/24` ishlatsa VPS marshrut jadvali
chalkashadi: bir xil manzilga ikkita peer da'vo qiladi va trafik
**tasodifan** birinchi mos peer'ga ketadi. Nosozlik «B bozorining
kamerasi A bozorining tasvirini ko'rsatyapti» ko'rinishida chiqadi —
ya'ni u ma'lumot sizishi.

**Bu fazadagi yechim:** `nvr_devices.tunnel_subnet` ustunidagi
**bozorlar aro global noyoblik** tekshiruvi (qisman UNIQUE indeks,
03-03). Onboarding paytida subnet band bo'lsa admin darhol xabar oladi
va boshqa diapazon tanlaydi.

**Hujjatlashtiriladi, IMPLEMENT QILINMAYDI:** bozor tomonida `1:1 NAT`.
Qurilma NVR ning `192.168.1.64` manzilini tunnel ichida noyob manzilga
(masalan `10.20.7.64`) tarjima qiladi va VPS faqat noyob manzilni
ko'radi. Bu to'qnashuvni **butunlay** yo'q qiladi va subnet noyobligini
talab qilmaydi, lekin har qurilmada qo'shimcha sozlash bosqichi
tug'diradi — D-14 ning «faqat rozetkaga ulaydi» qoidasiga zid. MVP
uchun noyoblik tekshiruvi yetarli; bozorlar soni o'ngacha chiqqanda
qayta ko'riladi.

---

## 4. Docker'da ishga tushirish

WireGuard konteyneri `compose.yaml` ga **bu rejada qo'shilmadi** va bu
ataylab: u `vpn` profili ostidagi **deploy** komponenti va uni dev/CI
muhitida ko'tarish ma'nosiz — WireGuard **kernel moduli** Windows dev
xostida umuman yo'q, CI konteynerida esa `NET_ADMIN` berilmagan.

8-fazadagi deploy runbook'i uchun tayyor bandi:

```yaml
  wireguard:
    profiles: ["vpn"]
    image: linuxserver/wireguard:1.0.20250521
    network_mode: host            # wg0 XOST tarmoq fazosida yaratiladi
    cap_add: [NET_ADMIN]          # SYS_MODULE uchun pastga qarang
    volumes:
      - ./ops/wireguard:/config
      - /lib/modules:/lib/modules:ro
    sysctls:
      net.ipv4.conf.all.src_valid_mark: 1
    restart: unless-stopped
```

| Qaror | Sabab |
|-------|-------|
| `network_mode: host` | `wg0` **xost** tarmoq nomlar fazosida yaratiladi va barcha konteynerlar (`go2rtc`, `core-api`) uni oddiy marshrut orqali ishlatadi. Alohida namespace'da har konteyner uchun `network_mode: service:wireguard` kerak bo'lardi |
| `/lib/modules:ro` | Xost **kernel** moduli ishlatiladi, `wireguard-go` userspace implementatsiyasi (sezilarli sekin) emas |
| **`SYS_MODULE` YO'Q** | Modulni **oldindan** yuklang: `modprobe wireguard && echo wireguard >> /etc/modules-load.d/wireguard.conf`. `SYS_MODULE` konteynerga xost kerneliga modul yuklash huquqini beradi — bu konteyner chegarasini amalda bekor qiladi. Imtiyozni kamaytirish **tavsiya emas, qoida** |
| `profiles: ["vpn"]` | Dev mashinada (simulyator bilan) VPN kerak emas |
| Litsenziya | `linuxserver/wireguard` — GPL-2.0 (WireGuard'ning o'zi). **Alohida, o'zgartirilmagan tarmoq servisi** — Postgres bilan bir xil poza. AGPL emas, CLAUDE.md cheklovini buzmaydi |

---

## 5. «Tunnel yagona yo'l» ni qanday isbotlaymiz (SC#5)

SC#5: *«tunnel o'chirilsa ulanish uziladi va NVR internetdan
to'g'ridan-to'g'ri ochiq emas».*

> ⚠ Sodda test — «tunnelni o'chir, ulanish uzilishini ko'r» — **CI'da
> bajarilmaydi va yolg'on ishonch beradi**: CI'da tunnel umuman yo'q,
> ya'ni test **har doim** «uzildi» deb o'tadi va **hech nima
> isbotlamaydi** (Pitfall 10).

Shuning uchun da'vo **uchta mustaqil qismga** ajratilgan va ikkitasi
**bugun, uskunasiz** o'lchanadi:

| # | Da'vo | Qanday isbotlanadi | Qayerda |
|---|-------|--------------------|---------|
| **1** | NVR manzili **xususiy** subnetda | `assert_private_host()` ommaviy IP'ni rad etadi | ✅ `tests/unit/test_nvr_host_validation.py` (CI) |
| **2** | `AllowedIPs` da `0.0.0.0/0` **yo'q** | Konfiguratsiya fayllari parse qilinadi | ✅ `tests/unit/test_wireguard_config.py` (CI) |
| **3** | Marshrut haqiqatan tunneldan ketadi | `ip route get <nvr_ip>` chiqishida `dev wg0` | ⚠ `ops/scripts/verify-tunnel.sh` — **faqat VPS'da**, deploy smoke-testi |

1 va 2 **regressiya** xavfini tutadi (kimdir keyinroq ommaviy IP
kiritadi yoki `AllowedIPs` ni kengaytiradi); 3 esa bir martalik deploy
tekshiruvi va u **go-live checklist'ining bandi**.

```bash
# VPS'da, deploy'dan keyin:
ops/scripts/verify-tunnel.sh 192.168.1.64
```
