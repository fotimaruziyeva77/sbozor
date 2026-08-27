# SBOZOR — frontend

Next.js 16 (App Router) admin paneli, kassir mobil rejimi va "yangi bozor" ustasi.

## Stek

| Qatlam    | Tanlov                                                        |
| --------- | ------------------------------------------------------------- |
| Framework | Next.js **16.2.12** — `proxy.ts` (`middleware.ts` **EMAS**)    |
| UI        | React **19.2.8**                                              |
| Typing    | TypeScript **5.9.3** (aniq pin — npm `latest` = 7.0.2, TAQIQ) |
| Styling   | Tailwind CSS **4.3.3** — CSS-first, `tailwind.config.js` YO'Q |
| i18n      | next-intl **4.13.4** — `uz-Latn` · `uz-Cyrl` · `ru`           |

## Buyruqlar

```bash
npm ci                 # bog'liqliklar (lock fayl bo'yicha)
npm run dev            # http://localhost:3000  →  /uz ga yo'naltiradi
npm run typecheck      # tsc --noEmit
npm run lint           # eslint . (Next 16 da `next lint` OLIB TASHLANGAN)
npm run i18n:gen       # messages/uz-Cyrl.json ni qayta hosil qiladi
npm run i18n:check     # drift + kalit-parity + ICU-parity darvozalari
npm run build          # standalone build (.next/standalone)
```

## Til fayllari

| Fayl                             | Kim tahrirlaydi                            |
| -------------------------------- | ------------------------------------------ |
| `messages/uz-Latn.json`          | **qo'lda** — asosiy manba                  |
| `messages/ru.json`               | **qo'lda**                                 |
| `messages/uz-Cyrl.overrides.json`| **qo'lda** — transliteratsiya tuzatishlari |
| `messages/uz-Cyrl.json`          | **GENERATSIYA** — qo'lda tegilmaydi (D-14) |

`uz-Latn.json` ga kalit qo'shgandan keyin `npm run i18n:gen` ni ishlatib,
hosil bo'lgan `uz-Cyrl.json` ni ham commit qiling — CI drift'ni bloklaydi.

## Dizayn tizimi

Tokenlar `src/app/globals.css` ichidagi `@theme` blokida (Apple-uslub minimal).
Primitivlar: `src/components/ui/{button,input,card}.tsx` — ularda **hech qanday
matn hardcode qilinmaydi**, barcha matn `next-intl` orqali keladi.

## Docker

```bash
docker build -t sbozor-frontend .
docker run --rm -p 3000:3000 sbozor-frontend
```
