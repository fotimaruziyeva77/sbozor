# Vendored go2rtc pleyeri — TEGILMAYDI

Bu katalogdagi `.js` fayllar **uchinchi tomon kodi** va ular
`AlexxIT/go2rtc` ning **`v1.9.14`** tegidan **bayt-ba-bayt** ko'chirilgan.
Ularni tahrirlash, formatlash yoki lint bilan "tuzatish" **taqiqlanadi**.

| Fayl | Manba (tegdagi yo'l) | Vazifa |
|------|----------------------|--------|
| `video-stream.js` | `www/video-stream.js` | `<video-stream>` web-komponenti (GUI qobig'i) |
| `video-rtc.js` | `www/video-rtc.js` | `VideoRTC` — WebRTC -> MSE -> HLS avtomatik tushish mantiqi |
| `LICENSE` | `LICENSE` | MIT matni (`Copyright (c) 2022 Alexey Khit`) |

## Nega ikkita fayl

`video-stream.js` ning birinchi qatori — `import {VideoRTC} from './video-rtc.js'`.
Ya'ni yolg'iz o'zi u **ishlamaydigan modul**, va yetishmagan bog'liqlikni
runtime'da go2rtc'dan yuklash **D-11 ni buzardi** (§8.7: frontend
go2rtc'ning HTTP yuzasiga hech qanday so'rov yubormaydi). Shu sababdan
ikkalasi ham vendored va **ikkalasining ham** SHA-256 i qayd etilgan.

## Yaxlitlik

Har `.js` faylning yonida `<fayl>.sha256` turadi — `sha256sum` formatida
bitta qator. Tekshiruv:

```bash
cd frontend/public/vendor/go2rtc && sha256sum -c *.sha256
```

CI darvozasi: `frontend/scripts/vendor-integrity.test.mjs` (G-7). U
katalogdagi **har** `.js` fayl uchun `.sha256` juftini talab qiladi, ya'ni
yangi uchinchi tomon fayli xeshsiz kirib kela olmaydi.

## Yangilash tartibi

1. Faqat `CLAUDE.md` dagi go2rtc versiyasi o'zgarganda.
2. **Alohida PR**, diff **to'liq o'qiladi** (`eval(`, `new Function`,
   o'z originidan tashqariga `fetch(`, `document.write`, obfuskatsiya).
3. `.sha256` fayllari qayta hisoblanadi.
4. Ko'rik natijasi
   `.planning/phases/03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi/03-UI-SPEC.md`
   §14.2 jadvaliga yoziladi.
