# SeaweedFS — dalil-kadrlarning S3-mos arxivi (CAM-07)

`storage` konteyneri barcha bozorlarning snapshot kadrlarini saqlaydi.
Bu kadrlar **bozor tashrifchilarining shaxsiy ma'lumoti** va O'zR
qonuni ostidagi ma'lumot — shuning uchun bu katalogdagi har bir qaror
xavfsizlik qarori, qulaylik qarori emas.

---

## 1. ⚠⚠ Rasmiy misol fayldagi TUZOQ — `anonymous`

SeaweedFS ning o'z `docker/compose/s3.json` misoli **aynan shunday**
boshlanadi (2026-08-04 da olindi):

```json
{ "identities": [ { "name": "anonymous", "actions": ["Read"] }, ... ] }
```

Bu yozuv **butun dalil arxivini autentifikatsiyasiz o'qishga ochadi.**
Misol faylni nusxalash barcha bozorlarning kadrlarini 8333-portga yeta
oladigan **har kimga** beradi — hech qanday kalit, hech qanday parol
so'ralmaydi va **hech qanday xato ham chiqmaydi**. Ombor bemalol
ishlayveradi; farq faqat kimdir uni topganda ko'rinadi.

Shuning uchun:

| Qoida | Nima uchun |
|-------|-----------|
| `anonymous` yozuvi **umuman bo'lmaydi** | Yuqoridagi sabab (T-04-01) |
| **Aynan bitta** identity — `sbozor-core-api` | Har qo'shimcha rekvizit — yana bitta oqish yuzasi va u hech kimga kerak emas |
| `Admin` amali **berilmaydi** | Ilova bucket yaratmaydi/o'chirmaydi — bucket bir marta, qo'lda yaratiladi (§3) |
| Har bir amal bucketga **qadalgan** (`Action:bucket`) | `"Read"` (bucketsiz) BUTUN klasterga tegishli bo'lardi |
| `ports:` bloki `compose.yaml` da **yozilmaydi** | Docker `iptables` qoidasi host firewall'ini chetlab o'tadi (T-04-02) |

Bularning hammasi **mexanik tekshiriladi**:
`tests/unit/test_storage_config.py` bu faylni `json.loads` bilan
**parse qiladi** (grep emas) va to'rt shartni ham qulflaydi, beshinchi
test esa `compose.yaml` da `storage` servisida `ports:` yo'qligini
tasdiqlaydi.

> `Action:bucket` va `Action:bucket/prefix` shakllari SeaweedFS tomonidan
> qo'llab-quvvatlanadi (`weed/s3api/auth_credentials.go` — *"Read:bucket",
> "Write:bucket/prefix" or "Write:bucket/prefix/\*" is scoped*).

---

## 2. Sozlash — `.env` bilan aynan bir xil naqsh

`s3.json` da **sirlar bor**, ya'ni u repoda **turmaydi**. Repoda faqat
`s3.json.example` bo'ladi — bu `.env.example` va
`ops/wireguard/wg0.conf.example` bilan aynan bir xil qaror.

```bash
cp ops/seaweedfs/s3.json.example ops/seaweedfs/s3.json
```

So'ng **uchta joyda bir xil** qiymat turishi shart:

| Joy | Kalit |
|-----|-------|
| `ops/seaweedfs/s3.json` | `credentials[0].accessKey` / `secretKey` |
| `.env` | `S3_ACCESS_KEY` / `S3_SECRET_KEY` |
| (o'qiydi) | `core-api`, `worker`, `scheduler` konteynerlari |

Kalitlarni hosil qilish:

```bash
python -c "import secrets;print('S3_ACCESS_KEY=' + secrets.token_urlsafe(24))"
python -c "import secrets;print('S3_SECRET_KEY=' + secrets.token_urlsafe(48))"
```

> ⚠ SeaweedFS `s3.json` ichida muhit o'zgaruvchisini **interpolatsiya
> qilmaydi** — `${S3_ACCESS_KEY}` yozuvi so'zma-so'z kalit sifatida
> qabul qilinadi. Qiymat faylga **literal** yoziladi va aynan shu
> sababdan fayl `.gitignore` da.

---

## 3. Bucket bir marta, qo'lda yaratiladi

Ilovada `create_bucket` chaqiruvi **yo'q** va bo'lmaydi ham (04-06):
u `Admin` huquqini talab qilardi, ya'ni yuqoridagi tor rekvizitni
kengaytirishga majbur qilardi. Bucket o'rnatishda bir marta yaratiladi:

```bash
printf 's3.bucket.create -name sbozor-snapshots\n' \
  | docker compose exec -T storage weed shell
```

Tekshirish:

```bash
printf 's3.bucket.list\n' | docker compose exec -T storage weed shell
#   sbozor-snapshots	size:0	logical:0	chunk:0
```

> ⚠ `weed shell -c "..."` **ISHLAMAYDI** (o'lchandi, SeaweedFS 4.40):
> `-c` bayrog'i mavjud emas va buyruq o'rniga `weed shell` ning
> yordam matni chiqadi — hech qanday xato kodisiz. Buyruqlar
> **stdin** dan o'qiladi, shuning uchun `printf ... | ... -T` shakli.

**Bitta bucket, `market_id` — birinchi prefiks** (bozor boshiga bucket
EMAS): yangi bozor onboardingiga «bucket yarat + IAM yozuvi qo'sh»
qadamini qo'shish self-service qoidasini buzardi.

> **Halol e'tirof:** bitta rekvizit — buzilgan `core-api` barcha
> bozorlarning kadrlarini o'qiy oladi. Bu **bazadagi bilan bir xil
> ishonch modeli** (`sbozor_app` roli GUC o'zgarishi bilan istalgan
> bozorga qaray oladi), ya'ni yangi teshik emas — mavjud chegaraning
> davomi. Lekin u shu yerda **nomlangan**, jimgina qoldirilmagan.

---

## 4. Nega SeaweedFS

| Variant | Verdikt |
|---------|---------|
| **SeaweedFS 4.40** | ✅ Apache-2.0, faol, ko'p mayda fayl uchun qurilgan — 175 JPEG/kun/bozor aynan shu holat |
| MinIO | ❌ Repo **2026-04-25 da arxivlangan** — xavfsizlik yamog'i yo'q. Shaxsiy ma'lumotni tashlab ketilgan demonda saqlash mumkin emas |
| Garage | ❌ AGPL-3.0 — CLAUDE.md taqig'i |
| RustFS | ❌ Hali pre-release; mualliflarining o'zi «prodda ishlatmang» deydi |
| Oddiy fayl tizimi | ⚠ 175 fayl/kun uchun texnik jihatdan yetarli, lekin S3 abstraksiyasi yo'qoladi va O'zbekiston hostingiga ko'chish qimmatlashadi |

Mijoz tomonida **`aiobotocore`** (S3 API), **hech qachon `minio-py`** —
shu tanlov omborni almashtirishni refaktor emas, **sozlama o'zgarishi**
qilib saqlaydi.

---

## 5. Zaxira nusxa

`seaweed` nomlangan volume `pgdata` bilan **bir xil toifada** va
8-fazadagi zaxira siyosati ikkalasini ham qamraydi (`restic` /
`rclone sync` offsite bucketga). Kadr arxivi yo'qolsa «band, lekin
to'lovsiz» da'vosining **rasm-dalili** yo'qoladi — ya'ni mahsulotning
asosiy argumenti.
