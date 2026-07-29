import { hasLocale } from "next-intl";
import { getRequestConfig } from "next-intl/server";

import { routing } from "./routing";

export default getRequestConfig(async ({ requestLocale }) => {
  const requested = await requestLocale;
  // D-15: mos kelmasa har doim uz-Latn ga tushadi (aniqlash yo'q).
  const locale = hasLocale(routing.locales, requested)
    ? requested
    : routing.defaultLocale;

  return {
    locale,
    messages: (await import(`../../messages/${locale}.json`)).default,
    // FOUND-05: ko'rsatish vaqt mintaqasi bitta joyda belgilanadi.
    // Biznes-kun chegarasi ham shu mintaqada (Asia/Tashkent, UTC+5, DST yo'q).
    timeZone: "Asia/Tashkent",
  };
});
