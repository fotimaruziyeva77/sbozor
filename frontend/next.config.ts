import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

/**
 * next-intl plaginini ulaydi. Standart bo'yicha `./src/i18n/request.ts` ni
 * qidiradi — struktura shu bilan mos. Fayl mavjud bo'lmasa Next konfiguratsiya
 * yuklanish bosqichidayoq yiqiladi.
 */
const withNextIntl = createNextIntlPlugin();

const nextConfig: NextConfig = {
  // Docker `runner` bosqichi uchun: `.next/standalone/server.js` hosil qiladi.
  output: "standalone",
  reactStrictMode: true,
  // DIQQAT: `experimental.useTypeScriptCli` ATAYIN O'RNATILMAGAN.
  // TS 7.0 Next 16 da faqat preview ortida (CLAUDE.md: TypeScript 5.9.3, 7.0.2 EMAS).
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: "http://[IP_ADDRESS]/api/v1/:path*",
      },
    ];
  },
};

export default withNextIntl(nextConfig);
