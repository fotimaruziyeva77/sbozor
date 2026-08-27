import type messages from "../messages/uz-Latn.json";
import type { routing } from "@/i18n/routing";

/**
 * next-intl uchun TypeScript kalit xavfsizligi.
 *
 * `uz-Latn.json` — kalitlarning yagona manbai. Shu augmentatsiya tufayli
 * `t('common.notExist')` KOMPILYATSIYA VAQTIDA xatoga aylanadi, runtime'da
 * `MISSING_MESSAGE` bo'lib chiqmaydi.
 *
 * ESKIRGAN: next-intl 3.x uslubidagi global `IntlMessages` tipi.
 */
declare module "next-intl" {
  interface AppConfig {
    Locale: (typeof routing.locales)[number];
    Messages: typeof messages;
  }
}
