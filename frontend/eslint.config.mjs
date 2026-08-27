import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";

/*
 * Next 16 da `next lint` OLIB TASHLANGAN — lint to'g'ridan-to'g'ri `eslint` CLI
 * va flat config orqali ishlaydi (`npm run lint` = `eslint .`).
 */
const eslintConfig = defineConfig([
  ...nextVitals,
  globalIgnores([
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    // Generatsiya artefakti — qo'lda tahrirlanmaydi (D-14).
    "messages/uz-Cyrl.json",
    /*
     * VENDORED UCHINCHI TOMON KODI — BAYT-BA-BAYT upstream nusxasi.
     *
     * Uni lint qilish TUZATISHGA majburlardi (`--fix` yoki qo'lda), va
     * har tuzatish SHA-256 ni o'zgartirib, `scripts/vendor-integrity.
     * test.mjs` ning butun mazmunini yo'q qilardi: qayd etilgan xesh
     * endi `AlexxIT/go2rtc` ning `v1.9.14` tegidagi fayl bilan
     * solishtirib bo'lmaydigan holga kelardi. Uslub darvozasi bu yerda
     * YAXLITLIK darvozasidan past turadi.
     */
    "public/vendor/**",
    /*
     * DESIGN-SYNC CHIQIMI — `ds-bundle/` va `.design-sync/previews/`
     * `design-sync` ko'nikmasi tomonidan GENERATSIYA qilinadi (ikkalasi
     * ham `.gitignore` da). Ichida React'ning o'zining bundle'i yotibdi,
     * va u `react-hooks/rules-of-hooks` ni 33 marta buzadi — chunki
     * qoida `useFiber`/`useThenable` kabi ichki funksiyalarni komponent
     * hooki deb o'ylaydi.
     *
     * ⛔ Buni e'tiborsiz qoldirish uslubdan chekinish EMAS: lint hech
     *   qachon yashil bo'lmasa, u DARVOZA bo'lishdan to'xtaydi — bizning
     *   `src/` dagi haqiqiy ogohlantirish 33 ta soxta xato orasida
     *   ko'rinmay ketadi (aynan shu bo'ldi 260819 da).
     */
    "ds-bundle/**",
    ".design-sync/**",
  ]),
]);

export default eslintConfig;
