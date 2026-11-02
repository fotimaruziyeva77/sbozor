"use client";

import {
  useFormatter,
  useLocale,
  useTimeZone,
  useTranslations,
} from "next-intl";

import { durationParts } from "@/components/parking/parking-data";
import { formatInstantDay } from "@/lib/format-day";
import { formatAmount, formatSoum } from "@/lib/format-number";

/**
 * Avtoturargoh hisobotining yozuv shakllari — bitta joyda, uch tilda.
 *
 * ⛔ Vaqt Toshkent mintaqasida: `NextIntlClientProvider` ning `timeZone`
 *    i ishlatiladi, ikkinchi manba yo'q (`format-day.ts` qoidasi).
 */
export function useParkingFormat() {
  const t = useTranslations("parkingReport");
  const format = useFormatter();
  const locale = useLocale();
  const timeZone = useTimeZone() ?? "Asia/Tashkent";

  function duration(minutes: number): string {
    const { days, hours, minutes: rest } = durationParts(minutes);
    /* «0 daq» emas: bir daqiqaga yetmagan turish ham turish. */
    if (days === 0 && hours === 0 && rest === 0) return t("duration.underMinute");
    if (days > 0) return t("duration.days", { d: days, h: hours });
    if (hours > 0 && rest > 0) return t("duration.hoursMinutes", { h: hours, m: rest });
    if (hours > 0) return t("duration.hours", { h: hours });
    return t("duration.minutes", { m: rest });
  }

  function time(iso: string): string {
    return format.dateTime(new Date(iso), { timeStyle: "short" });
  }

  function day(iso: string): string {
    return formatInstantDay(format, new Date(iso), locale, timeZone);
  }

  return {
    duration,
    time,
    day,
    count: (value: number) => formatAmount(format, value, locale),
    soum: (value: number) => formatSoum(format, value, locale),
  };
}
