# camagent-gateway — tunnelsiz bozorlar kanali

> **Vendoring:** `agent_gateway/` nusxasi qo'lda tahrirlanmaydi
> (`VENDORED.md`). Haqiqat manbai — CamAgent repozi (`Kamera/`),
> yangilash: `python tools/sync_to_sbozor.py` (o'sha repodan).

## Bu nima va nega kerak

SBOZOR'ning asosiy kadr olish yo'li — VPS'dan WireGuard tunnel orqali
NVR'ga to'g'ridan-to'g'ri ulanish (`jobs/capture.py`). Lekin tunnel har
bozorda ham qurilavermaydi: router almashtirish kerak, provayder CGNAT
beradi, joyida texnik yo'q.

CamAgent — teskari model: bozor kompyuteriga bitta `camagent.exe`
o'rnatiladi, u NVR'dan jadval bo'yicha o'zi rasm oladi va **tashqariga**
shu serverga yuboradi. Bozor modemida port ochilmaydi, NVR internetga
chiqarilmaydi, tunnel kerak emas. Bu servis — o'sha agentlarning server
tomoni: aktivatsiya, WebSocket boshqaruv, rasm qabul, vaqtinchalik panel.

**Protokol muzlatilgan** (`docs/protocol.md` shu papkada): v1 maydonlari
o'zgarmaydi — dalada qolgan eski agentlar ishlashda davom etishi shart.

## Ishga tushirish

1. `.env` ga kalit qo'shing (bo'sh qolsa har restart'da yangi kalit):

       CAMAGENT_GW_ADMIN_TOKEN=<python -c "import secrets;print(secrets.token_urlsafe(24))">

2. Ko'taring (asosiy compose BUZILMAYDI — bu ixtiyoriy qatlam):

       docker compose -f compose.yaml -f compose.camagent.yml up -d --build --wait camagent-gateway

3. nginx allaqachon `/api/v1/agent/` ni shu servisga yo'naltiradi
   (`ops/nginx/app.inc`) — nginx'ni qayta yuklang:

       docker compose --profile proxy up -d --force-recreate nginx

4. Panel (vaqtinchalik dev-panel; tashqariga OCHILMAGAN):

       ssh -L 8787:127.0.0.1:8787 <server>

   va `compose.camagent.yml` dagi `ports:` izohini oching, yoki panelga
   umuman kirmasdan aktivatsiya kodini quyidagicha yarating:

       docker compose -f compose.yaml -f compose.camagent.yml exec camagent-gateway \
         python -c "from agent_gateway.db import GatewayDB; \
print(GatewayDB('/data/gateway.db').create_code('Karmana bozori','karmana-01'))"

   `key_prefix` (ikkinchi argument) — sbozor'dagi bozor identifikatori:
   keyin har rasm kaliti shu prefiks bilan boshlanadi va rasm qaysi
   bozorniki ekani shundan ma'lum bo'ladi.

5. Obyektda `camagent.exe --setup` → server manzili `https://<PUBLIC_DOMAIN>`,
   aktivatsiya kodi, NVR login/parol. To'liq dala ro'yxati CamAgent
   repozida: `docs/deployment.md`.

## Ma'lumot qayerda yotadi

| Nima | Qayerda |
|---|---|
| Rasmlar (JPEG + `.json` sidecar) | SeaweedFS `sbozor-snapshots` bucket, `camagent/<sana>/...` prefiksi |
| Metadata (agentlar, navbatlar, hodisalar, seanslar) | `camagent_data` volume → `/data/gateway.db` (SQLite, WAL) |

`camagent/` prefiksi ATAYIN core-api'ning kalit sxemasidan
(`{market_uuid}/{sana}/{camera_uuid}/{HHMM}.jpg`) tashqarida: retention
va orphan supurgilari faqat `{uuid}/{sana}/` prefikslarini ko'radi, ya'ni
agent rasmlariga tegmaydi. Alohida bucket ham, `s3.json` da yangi
identity ham kerak emas (`test_exactly_one_identity` darvozasi buziladi).

**Zaxira:** `camagent_data` volume'ini restic ro'yxatiga qo'shing —
rasmlar S3'da (u allaqachon zaxiralanadi), lekin gateway.db yo'qolsa
agentlar qayta aktivatsiya qilinishi kerak bo'ladi.

## sbozor bilan chegara (hozircha ATAYIN alohida)

Agent rasmlari sbozor'ning `snapshots`/`occupancy` domeniga **hali
yozilmaydi** — bu ongli qaror, kamchilik emas:

* `CaptureMethod` "aynan uchta" deb qulflangan (D-06) — to'rtinchi
  usulni kiritish sbozor jamoasining arxitektura qarori;
* `capture_runs` ijara/slot modeli server-pull uchun yozilgan, push
  modeliga bevosita to'g'ri kelmaydi.

Tahlil quvuriga ulash kerak bo'lganda ikki tayyor o'qish nuqtasi bor:
`GatewayDB.list_snapshots()` (metadata, idem_key ichida bozor prefiksi)
va S3 `camagent/` prefiksi (rasm + sidecar). Bu qadam CamAgent repodagi
`docs/integration.md` da "keyingi ish" sifatida hujjatlangan.

## Jonli video (ixtiyoriy)

`.env` ga `CAMAGENT_MEDIA_HOST` (+ kerak bo'lsa TURN) yozilganda va
MediaMTX binari `/data/media/mediamtx` ga qo'yilganda panel WebRTC'da
jonli ko'rsatadi; 8554/tcp — yagona yangi tashqi port. Busiz panel
"yangilanuvchi rasm" rejimida ishlayveradi. Tafsilot: CamAgent repo,
`docs/integration.md` 6-bo'lim.

## PostgreSQL'ga o'tish (2-obyektdan keyin, ixtiyoriy)

`GatewayDB` interfeysi bitta sinf ichida — SQLite'ni PostgreSQL bilan
almashtirish metod imzolarini o'zgartirmaydi (~yarim kun, CamAgent repo
`docs/integration.md` 3-bo'lim). 12 bozorgacha SQLite o'lchangan va
yetarli: 3 360 rasm/kun yuk sinovida xatosiz.
