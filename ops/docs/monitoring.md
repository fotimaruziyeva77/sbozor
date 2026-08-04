# Kuzatuv va alertlar — operatsion yo'riqnoma (FOUND-06, D-19..D-22)

> **Bu hujjat darvoza EMAS.** U operatsion tartib: kuzatuv qanday
> ishlashini, uning **halol chegarasini** va odam qo'li bilan
> bajariladigan uch bandni yozadi. Kodning darvozalari
> `tests/integration/test_alerting.py` va `tests/integration/test_retention.py`
> da.

---

## 0. Bir jumlada

**Tizim «xato chiqdi» ga emas, «MUVAFFAQIYAT SIGNALI KELMADI» ga alert
beradi** — CLAUDE.md ning talabi shu, va u butun bo'limning
arxitekturasini belgilaydi.

Farq amaliy: kod umuman ishga tushmasa **xato ham chiqmaydi**. Sentry jim,
jurnal jim, Telegram jim — va bozor uch kundan beri kadrsiz. Shuning uchun
kuzatuv uch qatlamli va har qatlam **boshqa turdagi jimlikni** ushlaydi.

---

## 1. Uch qatlam — va har biri nimani ushlaydi

| # | Qatlam | Qayerda ishlaydi | Qanday jimlikni ushlaydi | v1 da |
|---|--------|------------------|--------------------------|-------|
| 1 | `capture_tick` + `alert_sweep` | **worker** konteyneri | «Ish umuman bajarilmadi» — reja materializatsiya qilingan, slot `missed` bo'lgan | ✅ qurilgan |
| 2 | Kunlik dayjest (20:00) | **worker** konteyneri | «Butun stek o'lik» — xabar **kelmasa** bu ham signal | ✅ qurilgan |
| 3 | Tashqi ping → `/internal/self-check` | **quti tashqarisida** | «VPS butunlay o'ldi» | ⚠ **ops ishi**, §4 |

### Halol chegara — buni yozib qo'yish shart

⛔ **VPS butunlay o'lsa ichkaridagi HECH BIR kod alert yubora olmaydi.**
Bu kamchilik emas, fizika: alert yuborish uchun ishlayotgan jarayon kerak.
1- va 2-qatlam faqat **qisman** nosozliklarni qoplaydi:

- worker o'lsa → `core-api` tirik qoladi va `/internal/self-check`
  `capture_tick` yurak urishining eskirganini ko'rsatadi;
- `core-api` o'lsa → nginx 502 beradi, ya'ni foydalanuvchi darhol ko'radi;
- **ikkalasi birga o'lsa** → faqat 3-qatlam (tashqi ping) yoki dayjestning
  **kelmagani** signal beradi.

Dayjest zaif, lekin narxi nolga yaqin: har kuni 20:00 da bitta xabar
keladi. **Ikki kun ketma-ket kelmasa — bu hodisa.**

---

## 2. `/internal/self-check` — nima qaytaradi

`GET /internal/self-check` (04-09 da quriladi) yurak urishlarini o'qiydi va
javob beradi:

```
200  {"ok": true}
503  {"ok": false, "stale": ["capture_tick"]}
```

### ⛔ U konteyner `healthcheck` ida ISHLATILMAYDI

`compose.yaml` dagi `healthcheck` — **liveness probe**: u yiqilsa Docker
konteynerni **qayta ishga tushiradi**.

`/internal/self-check` esa **bog'liqlik holatini** o'lchaydi (worker
tirikmi). Ikkalasini bog'lash klassik anti-naqsh bo'lardi:

> worker'ning yurak urishi eskirgani uchun **sog'lom `core-api` qayta
> ishga tushiriladi** — bu hech nimani tuzatmaydi, faqat uzilishni
> uzaytiradi va sababni **yashiradi** (restart jurnaldagi izni yo'qotadi).

Shuning uchun `compose.yaml` ning `core-api` bloki `/healthz` ni
ishlatadi, `/internal/self-check` ni esa **faqat tashqi kuzatuvchi**
so'raydi.

---

## 3. Alertlar — nima keladi va nima kelmaydi

### Guruhlash

25 kamera × 3 slot = 75 yiqilish → **bitta xabar**. Bo'g'ilgan takrorlar
yo'qolmaydi: ular `alert_events.occurrences` da sanaladi va UI ularni
«So'nggi soatda yana N marta» qatori bilan ko'rsatadi.

| Qoida | Qiymat |
|-------|--------|
| Debounce (bir xil bozor + kalit + subyekt) | **60 daqiqa** |
| Eskalatsiya `warning` → `critical` | **3 soat** |
| Yurak urishining eskirishi | **26 soat** |
| Kamera «offline» deb e'lon qilinadi | **3 ketma-ket slot** yoki bitta slotda **≥30 %** kamera |
| Bozor «ko'r» deb e'lon qilinadi | ketma-ket **2 slot** 0 % |
| Disk bosimi | **≥85 %** |

⚠ **Eskalatsiya — DARAJA, chastota emas.** Muammo davom etsa xabarlar
tezlashmaydi; ularning darajasi oshadi.

### ⛔ HECH QACHON bo'g'ilmaydigan hodisalar

Bu ro'yxat kodda **metadan hosila** (`ALERT_META`), qo'lda takrorlanmaydi:

| Kalit | Nima uchun bo'g'ilmaydi |
|-------|-------------------------|
| `capture_stopped` | Bozor ko'r bo'lib qoldi — kunlik hisobning butun asosi yo'qoladi |
| `camera_offline` | Uzluksiz offline o'z-o'zidan tuzalmaydi |
| `backup_stale` | Ma'lumot yo'qotish xavfi (FOUND-07 ning yagona kuzatuv nuqtasi) |
| `disk_pressure` | Disk to'lsa **hech qanday alert yuborib bo'lmaydi** |
| `nvr_account_locked` | Vaqt sezgir: qulf oynasi bor va uni kutish kerak |
| `capture_credential_unreadable` | Konfiguratsiya nosozligi; hech qachon o'zi tuzalmaydi |

### ⛔ Alertga kadr rasmi HECH QACHON biriktirilmaydi (D-19)

Dalil-kadrlar bozor tashrifchilarining **shaxsiy ma'lumoti**, Telegram
serverlari esa loyiha zimmasiga olgan **O'zR data-rezidentlik
chegarasidan tashqarida**. Shuning uchun rasm biriktiruvchi Telegram
metodi kodda **umuman yozilmagan** — bu sozlama emas, struktura.

Xabarda faqat matn, kalitlar va sonlar bo'ladi.

---

## 4. Ops bandlari — odam qo'li bilan (uch band)

### 4.1 Telegram botini sozlash

| # | Qadam | Natija |
|---|-------|--------|
| 1 | Telegram'da [@BotFather](https://t.me/BotFather) ga `/newbot` yuboring | Bot nomi va `@username` so'raladi |
| 2 | Javobdagi **tokenni** nusxa oling | `1234567890:AA...` ko'rinishida |
| 3 | Tokenni serverdagi `.env` ga yozing: `TELEGRAM_BOT_TOKEN=...` | ⚠ Repozitoriyga **hech qachon** commit qilmang |

⚠ **Token — sir.** U bilan istalgan odam bot nomidan xabar yubora oladi.
Kodda u `SecretStr` va `censor_secrets` ro'yxatida, ya'ni jurnalga va
Sentry'ga tushmaydi — lekin `.env` faylining o'zini himoya qilish **ops
ishi**.

### 4.2 Chat ID ni olish

| # | Qadam | Natija |
|---|-------|--------|
| 1 | Ops guruhini yarating va botni unga **admin** sifatida qo'shing | — |
| 2 | Guruhga istalgan xabar yozing | — |
| 3 | Brauzerda oching: `https://api.telegram.org/bot<TOKEN>/getUpdates` | JSON javob |
| 4 | Javobdagi `"chat":{"id":-100...}` qiymatini oling | Guruh ID **manfiy** bo'ladi |
| 5 | `.env` ga yozing: `TELEGRAM_CHAT_ID=-100...` | — |

⚠ **Guruhda chegara qattiqroq:** Telegram guruhga daqiqasiga ~20 xabar
beradi. Tizimning guruhlashi aynan shu sababdan majburiy.

### 4.3 Birinchi test xabari

`.env` yangilangandan keyin worker'ni qayta ishga tushiring:

```bash
docker compose up -d --build worker scheduler
docker compose logs worker --tail 20 | grep -E "worker_started|alerts_disabled"
```

- `worker_started ... alerts=True` → alertlar **yoqilgan**;
- `alerts_disabled` → token yoki chat ID **yo'q**. Tizim ishlashda davom
  etadi (kadr olish to'xtamaydi), lekin **hech qanday xabar kelmaydi**.

⚠ **Jim ishlash ATAYIN taqiqlangan:** ogohlantirishsiz bo'sh token «alert
bor deb o'ylash» yolg'onini tug'diradi. Shuning uchun har ishga tushishda
jurnalga bitta satr yoziladi va UI'da `notified_at` `NULL` bo'lgan alert
«Telegram xabari **yuborilmadi**» deb ko'rsatiladi.

Birinchi haqiqiy xabarni kutish: keyingi **20:00** dagi dayjest.

---

## 5. Tashqi dead-man's switch (D-21) — bitta URL, kod emas

⚠ **v1 da bu qatlam uchun kod YOZILMAYDI.** U bitta URL sozlash — ya'ni
ops ishi, va uni kodga aylantirish yangi bog'liqlik hamda yangi nosozlik
nuqtasi qo'shardi.

### healthchecks.io bilan (tavsiya etiladi — bepul reja yetadi)

| # | Qadam |
|---|-------|
| 1 | [healthchecks.io](https://healthchecks.io) da hisob oching |
| 2 | **Add Check** → nomi: `sbozor-self-check` |
| 3 | **Schedule** → `Period: 10 minutes`, `Grace: 10 minutes` |
| 4 | Turi: **"Check is up if URL returns 2xx"** (ba'zi rejalarda *HTTP check*) |
| 5 | URL: `https://<domen>/internal/self-check` |
| 6 | **Notification** → o'z Telegram/email kanalingizni ulang |

### UptimeRobot bilan

| # | Qadam |
|---|-------|
| 1 | **Add New Monitor** → `Monitor Type: HTTP(s)` |
| 2 | URL: `https://<domen>/internal/self-check` |
| 3 | `Monitoring Interval: 5 minutes` |
| 4 | `Alert Contacts` — Telegram yoki email |

### Nima uchun bu qatlam boshqacha

Yuqoridagi 1- va 2-qatlam **bizning kodimiz** bo'lgani uchun bizning
kodimiz bilan birga o'ladi. 3-qatlam esa **boshqa provayderning**
serverida ishlaydi va u bizning VPS bilan bir vaqtda yiqilmaydi.

⚠ **Tekshirish:** sozlagandan keyin worker'ni ataylab to'xtatib ko'ring
(`docker compose stop worker`) va 10–20 daqiqadan keyin tashqi
kuzatuvchidan xabar kelishini kuting. Xabar **kelmasa** — sozlama ishlamayapti
va uni shu paytda tuzatish kerak, hodisa paytida emas.

---

## 6. Kunlik operatsion tekshiruv (30 soniya)

| # | Savol | Qayerdan |
|---|-------|----------|
| 1 | Kechagi dayjest keldimi? | Telegram guruhi |
| 2 | Ochiq alert bormi? | `/snapshots` sahifasidagi B zonasi |
| 3 | `capture_tick` tirikmi? | `GET /internal/self-check` → `{"ok": true}` |

⚠ **To'g'ri sozlangan tizimda alert KAMDAN-KAM keladi va aynan shu narsa
uni ishonchli qiladi.** Har kuni bir necha alert kelayotgan bo'lsa —
chegaralarni sozlash vaqti keldi, alertlarni o'chirishning emas.

---

## 7. Saqlash siyosati — ops uchun

| Yosh | Holat | Nima bo'ladi |
|------|-------|--------------|
| 0–90 kun | `full` | Original JPEG |
| 91–455 kun | `compressed` | Qayta kodlangan, **AYNAN o'sha kalit** |
| 455+ kun | `purged` | Obyekt o'chirildi, **QATOR QOLADI** |

⛔ **`snapshots` qatori HECH QACHON o'chirilmaydi.** 6-fazadagi hisob
yozuvlari dalil-kadrga bog'lanadi, ya'ni qatorni yo'q qilish dalil
havolasini uzardi. `purged` qator «kadr mavjud edi, arxivdan `<sana>` da
chiqarildi» deb **halol** ko'rsatiladi.

Kunlik yugurish: **03:20 (Toshkent)**, `retention.daily`.

⚠ **90 kunlik siyosat kod darajasida sinaladi, lekin 90 HAQIQIY kun
davomida sinalmagan.** Testlar mexanizmni isbotlaydi (chegara nolga
qo'yiladi va bugungi kadr darhol siqiladi); siyosatning bir yil davomida
ishlab turishini faqat vaqt isbotlaydi. Bu band `04-VALIDATION.md` da
**Manual-Only** sifatida, egasi **Ops** bilan turadi.

**Nazorat qilish kerak bo'lgan yagona son:** `system_heartbeats` dagi
`retention` qatorining `last_seen_at` i. U 26 soatdan eskirsa
`retention_stale` alerti keladi.

---

*Aloqador hujjatlar: `ops/docs/nvr-onboarding.md`, `ops/seaweedfs/README.md`.*
