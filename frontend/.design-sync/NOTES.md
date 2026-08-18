# design-sync — repo eslatmalari (SBOZOR frontend)

- **Bu repo kutubxona emas, Next.js ilovasi.** Shuning uchun `dist/` yo'q va
  eksport yuzasi qo'lda yozilgan: `.design-sync/ds-entry.ts` — `src/components/ui/**`
  dagi haqiqiy komponentlarni qayta eksport qiladi. Yangi UI komponent
  qo'shilsa, o'sha faylga VA `cfg.componentSrcMap` ga qo'shiladi.
- **`.d.ts` daraxti generatsiya qilinadi.** `npx tsc -p .design-sync/tsconfig.dts.json`
  → `types/` (gitignore'da). Busiz prop kontrakti `[key: string]: unknown` bo'lib
  qoladi va dizayn agenti API'ni ko'rmaydi. **Har sync oldidan qayta yurgizilsin.**
- **CSS Tailwind v4 CLI bilan kompilyatsiya qilinadi:**
  `./.ds-sync/node_modules/.bin/tailwindcss -i src/app/globals.css -o .design-sync/ds-styles.css`
  (`cfg.cssEntry` shu faylga qaraydi). `globals.css` ning o'zi `@import "tailwindcss"`
  bo'lgani uchun to'g'ridan-to'g'ri ishlatib bo'lmaydi.
- **`[FONT_MISSING] Inter` — ONGLI holat.** Ilova brend shrift yubormaydi:
  `--font-sans` tizim steki bo'lib, `Inter` unda shunchaki zaxira nom. Marketing
  yuzalari (landing/login) alohida `Instrument Sans` (next/font) ishlatadi va u
  komponentlarning emas, sahifaning qismi. Shuning uchun `runtimeFontPrefixes: ["Inter"]`
  bilan ogohlantirish so'ndirilgan — shrift yuborish XATO bo'lardi.
- **Ma'lum render ogohlantirishlari:** `CardHeader`/`CardContent` yolg'iz holda
  bo'sh render bo'ladi (ular `Card` ning ichki qismlari) — ko'rinishlari `Card`
  kompozitsiyasi sifatida yozilgan.

## Re-sync xavflari
- `types/` va `.design-sync/ds-styles.css` — generatsiya mahsuloti, gitignore'da.
  Ular yangilanmasa, sync ESKI tip va ESKI uslub bilan chiqadi. Ikkalasini ham
  build oldidan qayta yaratish shart (yuqoridagi ikki buyruq).
- `ds-entry.ts` qo'lda yuritiladi — yangi komponent unutilsa, u sync'ga umuman
  tushmaydi va buni hech qanday darvoza ushlamaydi.
