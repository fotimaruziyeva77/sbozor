"use client";

import { useTranslations } from "next-intl";

/*
 * =============================================================================
 * NISBIY VAQT — «12 soat oldin» (260828).
 *
 * ⛔⛔ `Intl.RelativeTimeFormat` ISHLATILMAYDI VA BU BRAUZER CHEKLOVI,
 *     USLUB TANLOVI EMAS.
 *
 *     Jonli o'lchandi (Chrome 141, `/uz/cameras`):
 *
 *       Node 24 (to'liq ICU):  uz-Latn -> «12 soat oldin»   ✓
 *       Chrome:                uz-Latn -> «-12 h»           ✗
 *                              resolvedOptions().locale = "uz"
 *
 *     Chrome'ning ICU ma'lumotlarida o'zbek tili uchun `relativeTime`
 *     naqshlari YO'Q va u jimgina RAQAMLI fallback'ga tushadi. Ekranda
 *     kamera qatorida «oxirgi ko'rilgan: -12 h» turardi — foydalanuvchi
 *     uchun ma'nosiz, va manfiy ishora hatto «kelajak» degan noto'g'ri
 *     taassurot berardi.
 *
 * ⛔ NEGA TESTLAR USHLAMADI: `vitest` jsdom ostida NODE ning Intl'ini
 *    ishlatadi, ya'ni test muhitida natija TO'G'RI edi. Bu sinf faqat
 *    haqiqiy brauzerda ko'rinadi — shuning uchun tuzatish ham brauzer
 *    Intl'iga tayanmaydi.
 *
 * ⚠ Chegara — SOATDA emas, MA'NODA: 1 daqiqagacha «hozirgina», 60
 *   daqiqagacha daqiqa, 24 soatgacha soat, keyin kun. Kattaroq oraliqda
 *   («oy», «yil») nisbiy vaqt umuman ma'nosiz — u yerda sana yoziladi va
 *   chaqiruvchi buni o'zi hal qiladi.
 * =============================================================================
 */

const MINUTE_MS = 60_000;
const HOUR_MS = 3_600_000;
const DAY_MS = 86_400_000;

/**
 * «12 soat oldin» / «3 daqiqa oldin» / «hozirgina» qaytaradigan funksiya.
 *
 * ⚠ HOOK, sof funksiya EMAS — VA BU TIP TALABI (260828, `tsc` ikki marta
 *   ushladi). `t` ni argument sifatida uzatish uchun uning tipini yozish
 *   kerak: qo'lda yozilgan `(key: string) => string` next-intl ning
 *   literal-kalitli tipiga mos kelmaydi, `ReturnType<typeof
 *   useTranslations>` esa «union type is too complex» beradi. Katalogni
 *   shu yerda o'qish ikkala muammoni ham yo'q qiladi.
 *
 * Returns:
 *     `(value, now) => string`. `now` ARGUMENT bo'lib qoladi:
 *     chaqiruvchi uni `useNow()` dan oladi va komponent sof qolaveradi.
 *     KELAJAKDAGI payt «hozirgina» beradi — agent va server soati bir
 *     necha soniyaga farq qilishi normal (CLAUDE.md §8) va uni
 *     «-1 daqiqa» deb ko'rsatish nosozlikka o'xshardi.
 */
export function useRelativePast(): (value: Date, now: Date) => string {
  const t = useTranslations();

  return (value: Date, now: Date): string => {
    const diff = now.getTime() - value.getTime();

    if (diff < MINUTE_MS) {
      return t("common.relativeJustNow");
    }
    if (diff < HOUR_MS) {
      return t("common.relativeMinutesAgo", {
        minutes: Math.floor(diff / MINUTE_MS),
      });
    }
    if (diff < DAY_MS) {
      return t("common.relativeHoursAgo", {
        hours: Math.floor(diff / HOUR_MS),
      });
    }
    return t("common.relativeDaysAgo", { days: Math.floor(diff / DAY_MS) });
  };
}
