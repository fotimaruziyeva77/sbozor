# Subdomenga qo'yish — SBOZOR

> Bir marta bajariladigan qadamlar. Har biri **nima uchun** kerakligi bilan.

## 0. Nima kerak

| Narsa | Kim beradi | Izoh |
|---|---|---|
| Subdomen (masalan `demo.sbozor.uz`) | Siz | DNS **A** yozuvi serverning IP'siga qaratilgan bo'lsin |
| Server (Contabo VPS) | Siz | Docker + Docker Compose v2 o'rnatilgan |
| 80 va 443 portlari ochiq | Siz | ACME tekshiruvi 80-portsiz ishlamaydi |
| Elektron pochta | Siz | Let's Encrypt ogohlantirishlari uchun |

⛔ DNS **oldindan** qaratilgan bo'lishi shart: sertifikat so'ralganda Let's Encrypt
domenni tekshiradi va u serverga tushmasa, so'rov rad etiladi.

## 1. Kodni serverga olish

```
git clone <repo> sbozor && cd sbozor
```

## 2. `.env` ni to'ldirish

`.env.example` dan nusxa oling va kamida shularni bering:

```
PUBLIC_DOMAIN=demo.sbozor.uz
NEXT_PUBLIC_SITE_URL=https://demo.sbozor.uz
POSTGRES_PASSWORD=<kuchli parol>
JWT_SECRET=<tasodifiy 64 belgi>
FERNET_KEY=<RTSP parollarini shifrlash kaliti>
TELEGRAM_BOT_TOKEN=<demo formasi xabari uchun>
NEXT_PUBLIC_CONTACT_PHONE=+998...
```

⛔ `NEXT_PUBLIC_*` build vaqtida qotadi — ularni o'zgartirsangiz frontend
**qayta qurilishi** shart.

## 2.1. ⛔ DEPLOY OLDI TEKSHIRUVI — o'tkazib yubormang

```bash
sh ops/scripts/preflight.sh
```

Skript hech nimani o'zgartirmaydi — faqat o'qiydi va **GO / NO-GO** aytadi.
U qaysi qiymat bo'sh ekanini va **oqibati nima bo'lishini** yozadi.

Nega kerak: deploy'ning nosozlik shakli o'lchangan va u har doim bir xil —
stack ko'tariladi, `docker compose ps` **yashil** ko'rinadi, lekin bitta
konteyner jimgina restart halqasida aylanadi. `cv-service` ONNX artefaktisiz
aynan shunday qiladi: har ~1 s da qayta ishga tushadi va **~80 % CPU** yeydi
(shu xostda o'lchangan). Sabab faqat `docker compose logs` da qoladi.

**CV artefaktisiz ONGLI ravishda chiqish:**

```bash
ALLOW_NO_CV=1 sh ops/scripts/preflight.sh
```

va stack'ni cv-service'siz ko'taring:

```bash
docker compose -f deployment/compose.yaml -f deployment/compose.prod.yml --profile proxy up -d --scale cv-service=0
```

⚠ Bunda **bandlik o'lchanmaydi**: «band, lekin to'lovsiz» hisoboti doim nol
ko'rsatadi va mahsulotning asosiy va'dasi ishlamaydi. Bu vaqtinchalik holat
bo'lishi kerak, doimiy emas.

## 3. Birinchi sertifikat

```
PUBLIC_DOMAIN=demo.sbozor.uz CERT_EMAIL=siz@example.com sh ops/scripts/first-cert.sh
```

Nima qiladi: vaqtinchalik, faqat ACME uchun nginx ko'taradi (production
konfiguratsiyasi sertifikatsiz **ko'tarilmaydi** — tovuq va tuxum), sertifikat
oladi, o'zini o'chiradi. Sertifikat allaqachon bo'lsa hech nima qilmaydi —
Let's Encrypt haftalik limitini yeb qo'ymaslik uchun.

## 4. Ishga tushirish

```
docker compose -f deployment/compose.yaml -f deployment/compose.prod.yml --profile proxy up -d
```

⛔ Fayllar **oshkora** sanaladi. `compose.override.yml` avtomatik qo'shiladi va
u **dev uchun** — bazani va API'ni tashqariga ochadi. Yuqoridagi buyruq uni
ataylab nomlamaydi.

## 5. Migratsiya va birinchi admin

```
docker compose -f deployment/compose.yaml -f deployment/compose.prod.yml --profile migrate run --rm migrate
```

### 5.1. Birinchi platforma admini

⛔⛔ **Bu qadam MAJBURIY va uni ILOVADAN bajarib bo'lmaydi.** Sabab
mexanik: `POST /api/v1/users` `USER_MANAGE` talab qiladi (ya'ni
allaqachon kirgan odam kerak), `UserRepository.create_user()` esa
`is_platform_admin=False` ni qotirib yozadi. Ya'ni API orqali birinchi
hisob **umuman tug'ilmaydi**. Bu qadam o'tkazib yuborilsa, deploy
tugaydi va tizimga **hech kim kira olmaydi**.

```
docker compose -f deployment/compose.yaml -f deployment/compose.prod.yml --profile migrate run --rm   -e BOOTSTRAP_PHONE=+998901234567   -e BOOTSTRAP_NAME="Ism Familiya"   -e BOOTSTRAP_PASSWORD='bir-martalik-parol'   migrate python ops/scripts/bootstrap_admin.py
```

- Parol **bir martalik**: birinchi kirishda ilova majburan almashtirishga
  yo'naltiradi (`must_change_password`). Doimiy parolni buyruqqa yozmang —
  u shell tarixida qoladi.
- Skript **idempotent**: telefon band bo'lsa hech nima o'zgartirmaydi va
  mavjud hisobning parolini **almashtirmaydi**.
- Keyingi hisoblar (bozor admini, direktor, kassir, nazoratchi) shu
  admin ostida **ilovadan** yaratiladi — bu yo'l qurilgan va ishlaydi.

Shundan keyin: kirish → parolni almashtirish → bozor sozlash sehrgari.

## 6. Tekshirish

```bash
sh ops/scripts/smoke.sh demo.sbozor.uz
```

Skript deploy NATIJASINI tashqaridan o'lchaydi — `preflight` konfiguratsiyani
(niyatni) o'qigan bo'lsa, bu brauzer ko'radigan tomonni tekshiradi:

| Band | Nima o'lchanadi |
|------|-----------------|
| 1 | HTTP → HTTPS yo'naltirish (301/307) |
| 2 | HTTPS landing 200 |
| 3 | Uchala til `/login` — SSG marshrutlari alohida |
| 4 | API tirikmi (200/401 — ikkalasi ham sog'lom) |
| 5 | ⛔ **go2rtc API taqiqi** — 403 (CVSS 9.1 zaifligi) |
| 6 | ⛔ **8080 porti tashqaridan yopiqmi** |
| 7 | Sertifikat muddati |

⛔ 5 va 6-bandlar konfiguratsiyada yozilganiga ISHONMAYDI — ular natijani
tashqaridan o'lchaydi. `docker compose ps` «yashil» deyishi mumkin, lekin
nginx noto'g'ri `server_name` bilan ko'tarilgan bo'lsa buni faqat shu yerdan
bilib olasiz.

Qo'lda ham ko'rish mumkin:

- `https://demo.sbozor.uz` — landing ochilishi kerak
- `https://demo.sbozor.uz/uz/login` — kirish sahifasi
- `http://demo.sbozor.uz` — HTTPS ga yo'naltirishi kerak
- Sertifikat: `docker compose ... exec nginx nginx -T | grep ssl_certificate`

## Sertifikat yangilanishi — avtomatik

`certbot` xizmati har 12 soatda urinadi; Let's Encrypt 30 kun qolganda
haqiqatan yangilaydi. **nginx har 6 soatda o'zini `reload` qiladi**
(`compose.prod.yml` dagi `command`), ya'ni yangilangan sertifikat
o'z-o'zidan kuchga kiradi — qo'lda hech narsa qilinmaydi.

⛔ Nega certbot'ning `--deploy-hook` i emas: hook nginx'ni qayta yuklashi
uchun certbot konteynerida docker CLI va **docker soketi** kerak bo'lardi
— bitta signal uchun ildizga teng huquq. `reload` graceful: eski ishchilar
joriy so'rovlarni tugatadi, uzilish bo'lmaydi.

Tekshirish (sertifikat muddati):

```
docker compose -f deployment/compose.yaml -f deployment/compose.prod.yml --profile proxy exec nginx   sh -c 'openssl x509 -enddate -noout -in /etc/letsencrypt/live/$PUBLIC_DOMAIN/fullchain.pem'
```

## Portlar

Production'da **faqat 80 va 443** ochiladi. `compose.yaml` dev uchun
`${PROXY_HOST_PORT:-8080}:80` ni e'lon qiladi va Compose `ports`
ro'yxatlarini **birlashtiradi** — shuning uchun `compose.prod.yml` da
`ports: !override` ishlatilgan. Usiz ilova serverda 8080-portda ham
ochilardi: TLS'ni, HSTS'ni va HTTPS yo'naltirishni chetlab o'tadigan
ikkinchi eshik, uni skaner birinchi kuni topadi.

Tekshirish:

```
docker compose -f deployment/compose.yaml -f deployment/compose.prod.yml --profile proxy config | grep -A3 published
```

## Nima production'da KO'TARILMAYDI

`nvr-sim` va `nvr-sim-rtsp` — soxta kamera oqimi. `compose.prod.yml` ularni
`profiles: ["never"]` bilan o'chiradi: real bozor ma'lumoti yonida
simulyatsiya kadrlari paydo bo'lishi mumkin emas.
