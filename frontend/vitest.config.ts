import { fileURLToPath } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

/*
 * React KOMPONENT testlari uchun (01-12).
 *
 * NEGA ALOHIDA YUGURTGICH: `frontend/scripts/*.test.mjs` sof funksiya
 * testlari va ular `node --test` ostida qoladi — ularga DOM ham, JSX
 * transformi ham kerak emas. Bu yerdagi konfiguratsiya faqat `src/` ichidagi
 * `*.test.tsx` fayllarini oladi, ya'ni ikkala to'plam bir-birini QAMRAMAYDI
 * va `npm test` ikkalasini ketma-ket ishga tushiradi.
 *
 * SABAB (CR-02): 1-fazadagi 37 test sof funksiya testlari edi, shuning uchun
 * "tugma `disabled` bo'lib qolgan" sinfidagi xato hech qachon avtomatik
 * ushlanmagan. `jsdom` + Testing Library shu bo'shliqni proporsional yopadi.
 * Playwright E2E ATAYIN bu yerda EMAS — u 8-fazaga qoldirilgan (OQ-2).
 */
export default defineConfig({
  plugins: [react()],
  resolve: {
    // `tsconfig.json` dagi `paths` ning aynan nusxasi — `@/lib/...` importlari
    // test ostida ham build'dagi bilan bir xil faylga tushishi uchun.
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    /*
     * ⛔ `.ts` HAM QAMRALADI (260828). Ilgari bu yerda faqat `*.test.tsx`
     *    turardi va `src/lib/` dagi sof funksiya testi `.ts` kengaytmasi
     *    bilan yozilsa JIMGINA o'tkazib yuborilardi — vitest «No test
     *    files found» demasdi ham, chunki boshqa 109 ta fayl topilardi.
     *
     *    `scripts/*.test.mjs` bilan qamrov MASALASI YO'Q: u boshqa
     *    papkada va `node --test` ostida qoladi (fayl boshidagi izoh).
     */
    include: ["src/**/*.test.{ts,tsx}"],
    /*
     * `restoreMocks` ATAYIN YOQILMAGAN: u `vi.spyOn` josuslarini tiklaydi,
     * lekin `vi.fn()` bilan qurilgan modul mock'larining chaqiruv TARIXINI
     * tozalamaydi — natijada bir testdagi chaqiruv keyingisining sanog'iga
     * qo'shilib ketadi. Shuning uchun test fayllari holatni o'zi, aniq
     * `vi.resetAllMocks()` bilan tozalaydi.
     *
     * DOM tozalash esa `vitest.setup.ts` dagi `cleanup()` zimmasida.
     */
  },
});
