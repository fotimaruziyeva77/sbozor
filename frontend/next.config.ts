import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Docker `runner` bosqichi uchun: `.next/standalone/server.js` hosil qiladi.
  output: "standalone",
  reactStrictMode: true,
  // DIQQAT: `experimental.useTypeScriptCli` ATAYIN O'RNATILMAGAN.
  // TS 7.0 Next 16 da faqat preview ortida (CLAUDE.md: TypeScript 5.9.3, 7.0.2 EMAS).
};

// next-intl plagini 2-taskda ulanadi (u `src/i18n/request.ts` mavjudligini
// konfiguratsiya yuklanish vaqtidayoq talab qiladi).
export default nextConfig;
