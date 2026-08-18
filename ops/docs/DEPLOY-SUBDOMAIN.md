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
docker compose -f compose.yaml -f compose.prod.yml --profile proxy up -d
```

⛔ Fayllar **oshkora** sanaladi. `compose.override.yml` avtomatik qo'shiladi va
u **dev uchun** — bazani va API'ni tashqariga ochadi. Yuqoridagi buyruq uni
ataylab nomlamaydi.

## 5. Migratsiya va birinchi admin

```
docker compose -f compose.yaml -f compose.prod.yml run --rm migrate
```

Platforma adminini yaratish va bozor sozlash sehrgari — ilovadan.

## 6. Tekshirish

- `https://demo.sbozor.uz` — landing ochilishi kerak
- `https://demo.sbozor.uz/uz/login` — kirish sahifasi
- `http://demo.sbozor.uz` — HTTPS ga yo'naltirishi kerak
- Sertifikat: `docker compose ... exec nginx nginx -T | grep ssl_certificate`

## Sertifikat yangilanishi

`certbot` xizmati stack bilan birga ko'tariladi va har 12 soatda urinadi;
Let's Encrypt 30 kun qolganda haqiqatan yangilaydi. Yangilangach nginx
**qayta yuklanishi** kerak — hozircha bu qo'lda:

```
docker compose -f compose.yaml -f compose.prod.yml exec nginx nginx -s reload
```

⚠ Bu ochiq band: avtomatik reload qo'shilmagan. 60 kunda bir marta qo'lda
bajarish yetarli, lekin uni unutish mumkin — kelajakda certbot `--deploy-hook`
bilan bog'lash kerak.

## Nima production'da KO'TARILMAYDI

`nvr-sim` va `nvr-sim-rtsp` — soxta kamera oqimi. `compose.prod.yml` ularni
`profiles: ["never"]` bilan o'chiradi: real bozor ma'lumoti yonida
simulyatsiya kadrlari paydo bo'lishi mumkin emas.
