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
  ]),
]);

export default eslintConfig;
