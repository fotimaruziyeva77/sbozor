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
  ]),
]);

export default eslintConfig;
