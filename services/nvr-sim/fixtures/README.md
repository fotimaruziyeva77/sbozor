# `nvr-sim` fixture'lari — kelib chiqishi va litsenziya

**Bu katalogdagi hech bir XML qo'lda yozilmagan.** Hammasi
`maciej-or/hikvision_next` (Home Assistant integratsiyasi) repozitoriyasining
`tests/fixtures/devices/*.json` dumplaridan **ajratib olingan**: o'sha dumplar
real Hikvision qurilmalaridan yozib olingan ISAPI javoblari.

## Nega bu qat'iy qoida

`03-RESEARCH.md` Pitfall 4 — **`simulator-confirms-itself`**:

> Agar sim XML'i bizning parserimiz kutgan shaklda qo'lda yozilsa, test faqat
> **«kod o'z taxminiga mos»** ekanini isbotlaydi. Bu yashil CI beradi va real
> qurilmada yiqiladi.

Shuning uchun: har faylning boshida manba izohi bor, va
`tests/unit/test_sim_fixtures.py` uni **mexanik** tekshiradi — sim'ni umuman
ishga tushirmasdan, faqat fayllarni o'qib. «Kimdir XML'ni parserga moslab
tuzatib qo'ydi» holati shu darvozada ko'rinadi.

## Fayllar

Manba repozitoriysi hammasida bir xil: **`github.com/maciej-or/hikvision_next`**,
yo'l — `tests/fixtures/devices/<qurilma>.json`.

| Fayl | Qurilma | ISAPI yo'li | Upstream commit | Blob sha1 | Olingan |
|---|---|---|---|---|---|
| `DS-7616NI-K2-deviceInfo.xml` | DS-7616NI-K2 (16 kanalli NVR) | `/ISAPI/System/deviceInfo` | `a0e59ea7426c` (2024-10-14) | `a145a70cf863…` | 2026-08-03 |
| `DS-7616NI-K2-inputProxyChannels.xml` | DS-7616NI-K2 | `/ISAPI/ContentMgmt/InputProxy/channels` | `a0e59ea7426c` (2024-10-14) | `a145a70cf863…` | 2026-08-03 |
| `DS-7616NI-K2-adminAccesses.xml` | DS-7616NI-K2 | `/ISAPI/Security/adminAccesses` | `a0e59ea7426c` (2024-10-14) | `a145a70cf863…` | 2026-08-03 |
| `DS-7732NI-M4-deviceInfo.xml` | DS-7732NI-M4 (32 kanalli NVR) | `/ISAPI/System/deviceInfo` | `c5f6cb85f6e8` (2024-12-04) | `92c315bd8dc1…` | 2026-08-03 |
| `DS-7732NI-M4-inputProxyChannels.xml` | DS-7732NI-M4 | `/ISAPI/ContentMgmt/InputProxy/channels` | `c5f6cb85f6e8` (2024-12-04) | `92c315bd8dc1…` | 2026-08-03 |
| `DS-2CD2346G2-ISU-deviceInfo.xml` | DS-2CD2346G2-ISU/SL (standalone IP-kamera) | `/ISAPI/System/deviceInfo` | `c83426ec2e19` (2024-11-24) | `89be73551de1…` | 2026-08-03 |
| `DS-2CD2346G2-ISU-videoInputChannels.xml` | DS-2CD2346G2-ISU/SL | `/ISAPI/System/Video/inputs/channels` | `c83426ec2e19` (2024-11-24) | `89be73551de1…` | 2026-08-03 |

**O'zgartirish: yo'q.** Element tartibi, atributlar, namespace va qiymatlar
dumpdan verbatim. Yagona qo'shimcha — fayl boshidagi manba izohi (u javobga
chiqmaydi: `sim/isapi.py::_load` uni olib tashlaydi, chunki real qurilma
bizning qaydimizni yubormaydi).

## Dumpdan olingan uchta topilma (ular kodga bevosita ta'sir qildi)

### 1. Namespace IKKI XIL — `hikvision.com` HAM, `isapi.org` HAM

| Fayl | Ildiz namespace'i |
|---|---|
| `DS-7616NI-K2-*` | `http://www.hikvision.com/ver20/XMLSchema` |
| `DS-2CD2346G2-ISU-*` | `http://www.hikvision.com/ver20/XMLSchema` |
| **`DS-7732NI-M4-*`** | **`http://www.isapi.org/ver20/XMLSchema`** |

`DS-7732NI-M4` (`@version="2.0"`) ISAPI 2.0 namespace'ini ishlatadi. Bu
**tadqiqotda kutilmagan** edi (`03-RESEARCH.md` faqat `hikvision.com` ni
keltirgan) va aynan qo'lda yozilgan fixture hech qachon ushlab bera olmaydigan
turdagi farq. Oqibati bevosita: kashfiyot parseri namespace-agnostik bo'lishi
**shart** (Pitfall 2), va `test_sim_fixtures.py` ikkala namespace'ning ham
korpusda qolishini qulflaydi — kimdir ularni «bir xillashtirib» qo'ymasin.

### 2. `@size` atributi YOLG'ON bo'lishi mumkin

`DS-7732NI-M4-inputProxyChannels.xml` da `<InputProxyChannelList ... size="14">`,
lekin `InputProxyChannel` elementlari **18 ta**. Ya'ni real qurilma o'z
atributiga zid qiymat yuboradi. Kashfiyot kodi elementlarni **sanashi** kerak,
`size` ga ishonmasligi. Sim buni qayta tug'diradi: `size` fixture'dan verbatim
qoladi va emitilgan kanallar soniga moslanmaydi.

### 3. NVR'da `/ISAPI/System/Video/inputs/channels` — **403**

`DS-7616NI-K2` da ham, `DS-7732NI-M4` da ham bu endpoint uchun dumpda aynan
`{"status_code": 403}` yozib olingan. Bu A.1 ning «`InputProxy` avtoritetli»
xulosasini **o'lchov bilan** tasdiqlaydi. Sim NVR rejimida shu 403 ni qaytaradi,
IP-kamera rejimida esa yozib olingan bitta kanalli ro'yxatni.

## Dumpda BO'LMAGAN, shuning uchun OCHIQ belgilangan taxminlar

Yashirin taxmin qabul qilinmaydi; ochiq belgilangani qabul qilinadi. Quyidagi
javoblar fixture EMAS — ular `sim/isapi.py` da quriladi va manbasi kod izohida
yozilgan:

| Javob | Manba | Qaerda |
|---|---|---|
| `/ISAPI/ContentMgmt/InputProxy/channels/status` | `03-RESEARCH.md` A.1 (`<online>` + `id` bo'yicha qo'shilish) | `isapi.py::_input_proxy_status` |
| `/ISAPI/System/time` | Hikvision ISAPI hujjatidagi `<Time>` | `isapi.py::_system_time` |
| `/ISAPI/System/capabilities` | qisqartirilgan `DeviceCap` (to'liq dump ~40 KB, ishlatilmaydi) | `isapi.py::CAPABILITIES_XML` |
| `/ISAPI/Streaming/channels/{id}` | dumpdagi `101` javobining tuzilmasi | `isapi.py::_streaming` |
| `.../picture` JPEG | sintetik 1×1 tasvir (git'ga binar fayl qo'shilmaydi) | `isapi.py::TINY_JPEG` |

## Litsenziya va atribut

Yuqori oqim repozitoriysida **e'lon qilingan litsenziya yo'q** (GitHub API
`license: null`, 2026-08-03 da tekshirildi). Bu yerdagi material — qurilma
javoblarining **faktik ma'lumoti** (interfeys faktlari: teg nomlari, port
raqamlari, model satrlari), ijodiy asar emas; manba yuqoridagi jadvalda va har
faylning izohida to'liq ko'rsatilgan.

Dumplar yuqori oqimda **allaqachon anonimlashtirilgan**: IP manzillar `1.0.0.x`
oralig'iga, seriya raqamlari nollarga, MAC manzillar tasodifiy qiymatga
almashtirilgan. Ya'ni bu yerda hech kimning haqiqiy tarmoq ma'lumoti yo'q.

Yangi fixture qo'shilsa: yuqoridagi jadvalga qator qo'shiladi va fayl boshiga
o'sha shakldagi izoh yoziladi — aks holda `test_sim_fixtures.py` qizaradi.
