# `deployment/` — orkestratsiya qatlami

Stekni ko'taradigan hamma narsa shu yerda: to'rtta compose fayli va
`.env`. Repo ildizida endi bitta ham docker fayli qolmadi.

| Fayl | Nima uchun |
|---|---|
| `compose.yaml` | Baza — barcha servislar, profillar, healthcheck'lar. `name: sbozor` shu yerda qadalgan |
| `compose.override.yml` | **Faqat dev**: `--reload`, manba bind-mount, portlar `127.0.0.1` ga |
| `compose.prod.yml` | **Faqat prod**: TLS, certbot, `ports: !override` |
| `compose.camagent.yml` | CamAgent darvozasi — ixtiyoriy qatlam |
| `.env` | Sirlar. Repoga **tushmaydi** (`.gitignore`) |
| `.env.example` | Namunа — `.env` shundan nusxa olinadi |

---

## Buyruqlar

```bash
# dev
docker compose -f deployment/compose.yaml -f deployment/compose.override.yml up -d
# yoki qisqasi:
npm run up

# prod
docker compose -f deployment/compose.yaml -f deployment/compose.prod.yml --profile proxy up -d

# prod + CamAgent
docker compose -f deployment/compose.yaml -f deployment/compose.prod.yml \
               -f deployment/compose.camagent.yml --profile proxy up -d
```

---

## Uchta tuzoq — hammasi o'lchangan, taxmin emas

**1. `-f` OSHKORA BERILADI, aks holda hech narsa topilmaydi.**
`docker compose` `compose.yaml` ni faqat **joriy papkadan** qidiradi.
Fayllar bu yerga ko'chgach avtomatik topish o'chdi. Bu baland nosozlik —
«no configuration file provided» — ya'ni jimgina o'tib ketmaydi.

**2. `-f` bergan zahoti `compose.override.yml` ning AVTOMATIK
birlashuvi ham o'chadi.** Dev buyrug'idan uni tushirib qoldirsangiz stek
`--reload` siz, bind-mount'siz va portlarsiz ko'tariladi. Bu **jim**
nosozlik: konteynerlar yashil, lekin kod o'zgarishi ilovaga yetib
bormaydi. Shuning uchun `package.json` dagi har skript ikkala faylni ham
sanaydi.

**3. `.env` SHU YERDA TURISHI SHART.** Compose uni **loyiha
papkasidan** o'qiydi, loyiha papkasi esa — birinchi `-f` faylining
papkasi, ya'ni `deployment/`. Ildizda qolsa nima bo'lishi o'lchandi:

```
exit=0
warning: The "POSTGRES_PASSWORD" variable is not set. Defaulting to a blank string.
warning: The "SBOZOR_OWNER_PASSWORD" variable is not set. ...
```

Ya'ni buyruq **muvaffaqiyatli tugaydi** va stek bo'sh parollar bilan
ko'tariladi. Bu uchala tuzoqning eng xavflisi.

---

## Serverda ko'chirish (bir martalik)

Repo yangilangach, `/srv/sbozor` da:

```bash
git pull
mv .env deployment/.env
```

Buyruqlardagi `-f compose.yaml` endi `-f deployment/compose.yaml`.
Loyiha nomi (`sbozor`) va hajmlar (`sbozor_pgdata`, …) **o'zgarmaydi** —
`name:` compose faylining o'zida qadalgan, papka nomiga bog'liq emas.

> Ko'chirish `docker compose config` bilan tekshirildi: dev, prod va
> camagent konfiguratsiyalari ko'chirishdan oldin va keyin **bayt-baytga
> bir xil** chiqdi.
