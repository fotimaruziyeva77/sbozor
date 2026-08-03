# NVR onboarding — bozorni ulash tartibi (CAM-01, CAM-02, CAM-08)

> **Bu hujjat darvoza EMAS.** U operatsion tartib: bozor kameralarini
> tizimga ulash uchun kim nima qilishini bosqichma-bosqich yozadi.
> Faza darvozasi `tests/integration/test_phase3_criteria.py` da va u
> simulyator ustida o'lchanadi (SC#7).

---

## 0. Bir jumlada

**Bozor ma'muriyati saytdan NVR manzili va login/parolni kiritadi —
boshqa hech narsa.** Model, kanallar soni, kamera nomlari, RTSP porti va
oqim manzillari tizim tomonidan **avtomat** aniqlanadi.

Bu ROADMAP ning 2026-08-01 dagi **self-service** qoidasining amaliy
shakli: *«yangi bozor kod yozmasdan, muhandis aralashuvisiz ulanadi»*.
Shu sababli quyidagi bo'limlarda masofaviy terminal, konfiguratsiya
fayli tahriri yoki skript ishga tushirish qadami **yo'q** — ular bo'lsa
mahsulotning asosiy raqobat ustunligi yo'qolardi.

Yagona istisno — **real qurilma birinchi marta ulanganda** bajariladigan
bir martalik zond (§4). U mahsulot oqimining bir qismi emas: u
**simulyatorning haqiqiyligini** tekshiradi va faqat ishlab chiquvchi
jamoa tomonidan, bir marta bajariladi.

---

## 1. Admin nima qiladi (saytda)

| # | Qadam | Natija |
|---|-------|--------|
| 1 | `/cameras` sahifasini ochadi | «NVR qurilmasi» bloki ko'rinadi |
| 2 | **Manzilni** kiritadi: `192.168.1.64` yoki `192.168.1.64:8080` | Port ko'rsatilmasa `80` olinadi |
| 3 | **Login** va **parolni** kiritadi | Parol Fernet bilan shifrlanib saqlanadi (SC#4) |
| 4 | *(ixtiyoriy)* «Ulanishni tekshirish» ni bosadi | Model, qurilma turi, kanallar soni va soat farqi ko'rinadi — **hech narsa saqlanmaydi** |
| 5 | «Saqlash va kameralarni topish» ni bosadi | Kashfiyot fon vazifasi boshlanadi |
| 6 | Panel to'lishini kutadi (odatda 5–20 s) | Uch hisoblagich: **qo'shildi / ulanmagan / o'zgarmadi** |
| 7 | Kerak bo'lsa kamerani qayta nomlaydi | Nom keyingi skanda **saqlanadi** (SC#2) |

**Boshqa hech narsa.** RTSP URL yozilmaydi, kanal raqami qo'lda
kiritilmaydi, model tanlanmaydi.

### Nima qilish KERAK EMAS

- ❌ RTSP manzilini qo'lda yozish — u kashf etilgan `host`, port va
  kanal raqamidan **hosil qilinadi**;
- ❌ kameralarni birma-bir qo'shish — kashfiyot barchasini o'zi yaratadi;
- ❌ kamerani «o'chirish» — o'chirish yo'li **umuman yo'q**, faqat
  **arxivlash** bor va u qaytariladi (D-10);
- ❌ «Ulanishni tekshirish» ni ketma-ket bosaverish — u 15 daqiqada
  **3 marta** bilan chegaralangan (qurilmaning qulflash hisoblagichi
  himoyalanadi).

### Xato chiqsa

Xato **hech qachon** «ulanmadi» degan quruq xabar bo'lmaydi: ekranda
**sabab** va **tuzatish yo'li** birga chiqadi (SC#3). To'liq ro'yxat —
§5.

⚠ **Parol/hisob xatolarida «Qayta urinish» tugmasi KO'RINMAYDI** va bu
nosozlik emas: Hikvision qurilmasi ~5 xato urinishdan keyin hisobni
30 daqiqaga qulflaydi va undan keyin **to'g'ri parol ham ishlamaydi**.
Tugma faqat qayta urinish qurilma holatini o'zgartirmaydigan hollarda
chiqadi.

---

## 2. On-site odam nima qiladi (bozorda)

Ikki qadam. Boshqa hech narsa.

1. **Qurilmani rozetkaga ulaydi.**
2. **Ethernet kabelini** NVR bilan **bir tarmoqqa** ulaydi (odatda
   NVR turgan kommutatorning bo'sh porti).

Xolos. Yashil chiroq yonganda ish tugadi.

**Kalitlar, `wg0.conf` va NVR subneti qurilmaga JO'NATISHDAN OLDIN
yoziladi** — bozorda hech kim hech nima sozlamaydi. Tartib takrorlanmaydi,
u yagona joyda: **[`ops/wireguard/README.md`](../wireguard/README.md) §2
(«CGNAT — bozor tomoni "rozetkaga ulaydi"»)**.

Bozor tomonidagi qurilma tunnelni **o'zi ochadi** (`PersistentKeepalive`),
ya'ni bozor ISP'sida oq IP ham, port-forward ham, statik manzil ham
**kerak emas** — CGNAT ostida ham ishlaydi.

---

## 3. Subnet to'qnashuvi (D-07)

**Muammo.** Ikkala bozor ham `192.168.1.0/24` ishlatsa (bu eng ko'p
uchraydigan uy/ofis diapazoni), VPS marshrut jadvali chalkashadi: bir
xil manzilga ikkita peer da'vo qiladi va trafik tasodifan birinchi mos
peer'ga ketadi. Nosozlik «B bozorining kamerasi A bozorining tasvirini
ko'rsatyapti» ko'rinishida chiqadi — ya'ni **ma'lumot sizishi**.

**Bu fazadagi yechim.** `nvr_devices.tunnel_subnet` ustunida **bozorlar
aro global noyoblik** (qisman UNIQUE indeks, 03-03). Ikkinchi bozor band
diapazonni yozmoqchi bo'lganda tizim onboarding paytida **aniq xato**
beradi va admin boshqa diapazon tanlaydi.

Amalda: yangi bozorga `192.168.<N>.0/24` beriladi, `<N>` — bozor tartib
raqami. Berilgan `tunnel_subnet` qiymati qurilma jo'natishdan oldin
`wg0.conf` ga yoziladi (§2 dagi havola).

**`1:1 NAT` — TASVIRLANADI, LEKIN IMPLEMENT QILINMAYDI.**

Muqobil yechim: bozor tomonidagi qurilma NVR ning `192.168.1.64`
manzilini tunnel ichida noyob manzilga (masalan `10.20.7.64`) tarjima
qiladi va VPS faqat noyob manzilni ko'radi. Bu to'qnashuvni **butunlay**
yo'q qiladi va subnet noyobligini umuman talab qilmaydi.

Nega **bugun qilinmaydi**: `1:1 NAT` har qurilmada qo'shimcha sozlash
bosqichi tug'diradi va bu §2 ning «faqat rozetkaga ulaydi» qoidasiga
zid. MVP uchun noyoblik tekshiruvi yetarli.

⚠ **Qaror qayta ochiladi** ikkinchi bozor kelganda yoki bozorlar soni
o'ntaga yaqinlashganda — qaysi biri oldin bo'lsa.

---

## 4. Real NVR kelganda: bir martalik zond

> Bu bo'lim **mahsulot oqimining qismi emas.** U bir marta, ishlab
> chiquvchi jamoa tomonidan bajariladi va uning maqsadi bitta:
> **simulyator real qurilmadan chetga chiqmaganini isbotlash.**

Butun 3-faza `services/nvr-sim` ustida o'lchangan. Bu Pitfall 4 ni
(`simulator-confirms-itself`) ochiq qoldiradi: sim fixture'lari real
firmware'ning shaklidan chetga chiqqan bo'lsa, CI yashil bo'lib turadi
va tizim **birinchi marta Karmanada** yiqiladi.

### 4.1. Zondni ishga tushirish

```sh
ops/scripts/verify-real-nvr.sh http://192.168.1.64 sbozor 'parol' > karmana-probe.json
```

Chiqish — **JSON**. U qurilmani **o'zgartirmaydi** (faqat `GET`).

### 4.2. Chiqishni fixture'lar bilan solishtirish

| JSON maydoni | `services/nvr-sim/fixtures/` dagi jufti | Farq nimani bildiradi |
|---|---|---|
| `device.model` / `deviceType` | `*-deviceInfo.xml` | Kashfiyotning tarmoqlanish nuqtasi (`NVR` -> `InputProxy`, `IPCamera` -> standalone) |
| `device.manufacturer_present` | `DS-7732NI-M4-deviceInfo.xml` (maydon **yo'q**) | `device_not_supported` sharti aynan shunga tayanadi (03-05) |
| `channels.counted` va `channels.ids` | `*-inputProxyChannels.xml` | Kanal raqamlash chetlanishi |
| `channels.size_attribute_matches_count` | `size="14"` vs 18 element (03-02) | `@size` ga ishonmaslik qarori |
| `rtsp.port` / `rtsp.discovered` | `*-adminAccesses.xml` | `false` bo'lsa mahsulot 554 ga tushadi va `rtsp_port_assumed` qo'yadi |
| `frames[].is_jpeg` / `bytes` | sim `TINY_JPEG` (160 bayt) qaytaradi | 4-fazaning kadr olish yo'li |
| `rtsp.concurrent_failed` | sim `nvr-sim:554` da RTSP xizmat qiladi (`nvr-sim-rtsp`), lekin sessiya limitini modellamaydi | **Sessiya limiti** — bugun o'lchanmagan qiymat (D-05) |

Xuddi shu savollarni `pytest -m hardware` ham beradi va u xulosani
**assert** shaklida chiqaradi:

```sh
REAL_NVR_URL=http://192.168.1.64 REAL_NVR_USER=sbozor REAL_NVR_PASSWORD='parol' \
  docker compose --profile test run --rm tests pytest -m hardware
```

⚠ Bu marker **fazani bloklamaydi** va standart zanjirda (`npm run test`,
`npm run gate`) umuman ishlamaydi — `pyproject.toml` dagi
`-m "not hardware"` standarti buni majburlaydi.

### 4.3. Farq topilsa

**Farq — SIM'NING nuqsoni, mahsulotning emas.** Tuzatish tartibi:

1. real javobni `services/nvr-sim/fixtures/` ga **tahrirsiz** yozish
   (fayl boshidagi provenance izohi bilan — `fixtures/README.md`);
2. `tests/unit/test_sim_fixtures.py` dagi kutilgan qiymatlarni
   yangilash;
3. `npm run test:sim` ni qayta bajarish — **qizargan test bor bo'lsa,
   u haqiqiy topilma**;
4. natijani
   `.planning/phases/03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi/03-VALIDATION.md`
   ning «Manual-Only Verifications» jadvaliga yozish.

Fixture'ni «to'g'rilash» uchun **mahsulot kodini o'zgartirmang**: avval
sim real qurilmaga o'xshasin, keyin qaysi test qizarganini ko'ring.

---

## 5. Diagnostika — xato kodlari

Ekrandagi matnlar bu yerda **takrorlanmaydi** (ikki manba bo'lib
ajralib ketardi). Har kod uchun sabab va tuzatish yo'li
`frontend/messages/uz-Latn.json` dagi `cameras.errorCause.<kod>` va
`cameras.errorFix.<kod>` kalitlarida — uch tilda. Quyida faqat
**operatsion qo'shimcha**: birinchi navbatda nima tekshiriladi.

| Kod | Birinchi tekshiriladigan narsa |
|---|---|
| `nvr_bad_credentials` | Login/parolni NVR ning o'z veb-interfeysida sinang. ⚠ Ketma-ket urinmang — hisob qulflanadi |
| `nvr_account_locked` | 30 daqiqa kuting. Qulf NVR tomonida, bizda emas — to'g'ri parol ham ishlamaydi |
| `nvr_user_no_permission` | NVR da hisobga «Remote: Live View / Playback» huquqi berilganini tekshiring |
| `nvr_clock_drift` | NVR sozlamalarida NTP ni yoqing (`Time Settings`). Farq >5 daqiqa bo'lsa Digest **butunlay** ishlamaydi |
| `nvr_digest_stale` | Odatda o'z-o'zidan tuzaladi. Takrorlansa — soat farqi (yuqoridagi qator) |
| `nvr_auth_mode_basic_only` | `Security -> Authentication -> Web Authentication` ni `digest/basic` ga qo'ying (faqat `digest` emas) |
| `nvr_unreachable` | Tunnel: `ops/scripts/verify-tunnel.sh <nvr-ip>`. Keyin — NVR manzili va porti |
| `nvr_isapi_unavailable` | Firmware'da ISAPI yoqilganini tekshiring; port `80`/`443` to'g'rimi |
| `nvr_tls_untrusted` | `https://` o'rniga `http://` bilan sinang — transport ishonchini **tunnel** beradi (SC#5) |
| `device_not_supported` | Qurilma Hikvision emas. Model nomini yozib oling — u `error_detail.model` da |
| `nvr_stream_limit` | NVR da ochiq masofaviy sessiyalarni yoping (mobil ilova, veb-interfeys). Chegara odatda 6–16 |
| `channel_offline` | **Bloklovchi emas** — kamera yozuvi baribir yaratiladi. Kanal kabelini va kamera quvvatini tekshiring |

⚠ Oxirgi qator muhim: `channel_offline` **kashfiyotni to'xtatmaydi**.
Qolgan kanallar odatdagidek qo'shiladi va oflayn kanal qator badge'i
bilan belgilanadi.

---

## 6. Nima noto'g'ri bo'lishi mumkin

| Alomat | Ehtimoliy sabab | Qayerga qarash |
|---|---|---|
| «Saqlash va kameralarni topish» 409 beradi | Shu NVR uchun skan **allaqachon ketyapti** | Javobdagi `run_id` bilan panel o'sha yugurishga ulanadi — kuting |
| Kashfiyot 180 soniyada tugamaydi | Fon vazifasi navbatda qolib ketgan | `worker` konteyneri ko'tarilganini tekshiring |
| Kameralar topildi, jonli tasvir yo'q | RTSP porti **taxmin qilingan** bo'lishi mumkin | Qurilma kartasida `rtsp_port_assumed` — u `true` bo'lsa birinchi gumondor shu |
| Qayta skandan keyin kamera nomi o'zgarib ketdi | Nom qo'lda o'zgartirilmagan edi | Qo'lda qo'yilgan nom **saqlanadi**; NVR nomi esa NVR'dan olinadi (SC#2) |
| Arxivlangan kamera qayta skanda tiklanmadi | **Kutilgan xulq** (D-10) | Ro'yxatda «Arxivni ko'rsatish» ni yoqing va «Qaytarish» ni bosing |
| Yangi bozorda subnet band deb chiqdi | D-07 noyoblik tekshiruvi | §3 — boshqa `192.168.<N>.0/24` tanlang |

---

*Oxirgi yangilanish: 2026-08-03 (03-11). Tegishli hujjatlar:
[`ops/wireguard/README.md`](../wireguard/README.md) (tunnel),
[`ops/data/karmana/README.md`](../data/karmana/README.md) (bozor ma'lumoti).*
