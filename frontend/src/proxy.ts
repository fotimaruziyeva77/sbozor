import createMiddleware from "next-intl/middleware";

import { routing } from "./i18n/routing";

/*
 * ⚠ BU FAYL `middleware.ts` EMAS.
 *
 * Next 16 da `middleware` fayl konventsiyasi `proxy` ga qayta nomlangan
 * (faqat Node runtime). Fayl `middleware.ts` deb nomlansa Next uni
 * UMUMAN YUKLAMAYDI va locale marshrutlash JIMGINA ishlamay qoladi —
 * xato ham, ogohlantirish ham chiqmaydi (T-01-08).
 */
export default createMiddleware(routing);

export const config = {
  // `api`, `_next`, `_vercel` va kengaytmali fayllar (`.png`, `.ico` ...) chetlab o'tiladi.
  matcher: "/((?!api|_next|_vercel|.*\\..*).*)",
};
