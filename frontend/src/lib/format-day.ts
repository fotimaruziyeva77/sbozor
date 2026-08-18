/*
 * =============================================================================
 * SANA-FAQAT QIYMATNI CHIZISH — ⛔ YAGONA YORDAMCHI (WR-07).
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ NIMANI TUZATADI VA NEGA U «KOSMETIKA» EMAS
 * -----------------------------------------------------------------------
 * `service_date` — ⛔ KALENDAR KUNI (`YYYY-MM-DD`), lahza EMAS. Uni
 * `new Date("2026-08-11T00:00:00")` bilan o'qish ⛔ MO'RT:
 *
 *   1. ofsetsiz satr ⛔ BRAUZERNING MAHALLIY mintaqasida talqin qilinadi;
 *   2. keyin u `Asia/Tashkent` da formatlanadi;
 *   3. Toshkentdan SHARQDAGI mijozda (Bishkek `+6`, Tokio `+9`) natija
 *      ⛔ BIR KUN OLDIN chiqadi.
 *
 * ⛔ VA IKKINCHI YARMI UNDAN YOMONROQ: SSR konteynerida `TZ=Asia/Tashkent`,
 *    brauzerda esa foydalanuvchining mintaqasi — ya'ni server va klient
 *    ⛔ BOSHQA-BOSHQA satr chizadi va React ⛔ GIDRATATSIYA
 *    NOMUVOFIQLIGIGA tushadi.
 *
 * Karmana pilotida hamma `+5` da, ya'ni bugun nosozlik KO'RINMAYDI — bu
 * aynan «tasodifan to'g'ri» toifasidagi kod va u shu sababdan
 * ⛔ MINTAQA ARGUMENTI bilan (jarayon mintaqasidan MUSTAQIL) o'lchanadi.
 *
 * -----------------------------------------------------------------------
 * ⛔ NEGA 12:00 UTC
 * -----------------------------------------------------------------------
 * Kun ⛔ TUSHGA langarlanadi, yarim tunga EMAS: |ofset| < 12 bo'lgan HAR
 * mintaqada kalendar kuni AYNI qoladi. Yarim tunga langarlangan lahza esa
 * manfiy ofsetda darhol oldingi kunga o'tadi (`format-day.test.tsx` ning
 * nazorat bandi buni o'lchaydi).
 *
 * ⚠ OCHIQ NARX: `+12` va undan katta ofset (Auckland, Kiritimati)
 *   chegaradan TASHQARIDA. Mahsulot O'zbekiston bozorlari uchun va u
 *   yerda ofset `+5`, yozgi vaqt YO'Q — ya'ni chegara amaliyotda hech
 *   qachon urilmaydi. Bu YASHIRILMAYDI: chegarani kengaytirish
 *   `Intl.DateTimeFormat` ga xom satr berishni talab qilardi va u
 *   `dateStyle` ni umuman bermasdi.
 *
 * -----------------------------------------------------------------------
 * ⛔ NEGA `null`, ⛔ ZAXIRA SANA EMAS
 * -----------------------------------------------------------------------
 * Yaroqsiz qiymatda `Date.now()` yoki epoxa qaytarish ⛔ TO'QILGAN sanani
 * ekranga O'LCHANGAN fakt bo'lib chizardi (05-14 darsi) — nizo hujjatida
 * (D-02) esa u BOSHQA kunni ko'rsatardi. Chaqiruvchi `null` shoxida
 * elementni ⛔ UMUMAN chizmaydi.
 * =============================================================================
 */

import type { useFormatter } from "next-intl";

import { isUzLatn, uzLatnDate } from "@/lib/uz-latn-date";

/** `YYYY-MM-DD` — shakl darvozasi (`day-picker.tsx` bilan AYNI naqsh). */
const ISO_DAY = /^(\d{4})-(\d{2})-(\d{2})$/u;

/**
 * `YYYY-MM-DD` -> mintaqadan MUSTAQIL `Date`, yoki ⛔ `null`.
 *
 * ⛔ SHAKL TEKSHIRUVI YETARLI EMAS: `2026-02-30` naqshga mos keladi,
 *    lekin MAVJUD EMAS. Shuning uchun qiymat UTC'da qayta qurilib,
 *    komponentalari bilan SOLISHTIRILADI (`isValidIsoDay` naqshi).
 */
export function isoDayToDate(day: string): Date | null {
  const match = ISO_DAY.exec(day);
  if (match === null) return null;

  const year = Number(match[1]);
  const month = Number(match[2]);
  const dayOfMonth = Number(match[3]);

  /* ⛔ 12:00 UTC — modul izohining «nega tush» bandi. */
  const parsed = new Date(Date.UTC(year, month - 1, dayOfMonth, 12));

  if (
    parsed.getUTCFullYear() !== year ||
    parsed.getUTCMonth() !== month - 1 ||
    parsed.getUTCDate() !== dayOfMonth
  ) {
    return null;
  }

  return parsed;
}

/**
 * ⛔ EKRANGA CHIZILADIGAN KUN — ⛔ YAGONA SHAKL (WR-07).
 *
 * =========================================================================
 * ⛔⛔ NEGA YORDAMCHI FORMATLAGICHNI ARGUMENT BO'LIB OLADI.
 *
 * `useFormatter()` — HOOK, ya'ni uni bu yerda chaqirish modulni React
 * render tsikliga bog'lardi va sof funksiya testini ⛔ IMKONSIZ qilardi.
 * Formatlagichni argument qilish esa locale/mintaqa qarorini
 * ⛔ PROVAYDERDA (bitta joyda) qoldiradi.
 *
 * ⛔ `timeZone` BU YERDA QO'LDA BERILMAYDI: `NextIntlClientProvider` uni
 *    allaqachon belgilaydi va ikkinchi manba ⛔ IKKI XIL SANA berardi —
 *    aynan WR-07 tuzatayotgan nosozlikning yangi nusxasi.
 *
 * ⛔ YAROQSIZ QIYMATDA XOM SATR QAYTADI, ⛔ TO'QILGAN SANA EMAS: xom
 *    `2026-08-11` — ⛔ ROST, faqat mahalliylashtirilmagan. Boshqa kunni
 *    chizish esa YOLG'ON bo'lardi (05-14 darsi).
 * =========================================================================
 */
export function formatBusinessDay(
  format: ReturnType<typeof useFormatter>,
  day: string,
  locale: string,
): string {
  const parsed = isoDayToDate(day);
  if (parsed === null) return day;
  /*
   * ⛔ O'zbek LOTIN yozuvi uchun `Intl` ildiz shablonini beradi («2026 M08
   *    15») — brauzer ICU'sida bu yozuvning oy nomlari yo'q (o'lchandi
   *    2026-08-18). Shuning uchun faqat SHU til uchun jadval bilan
   *    yoziladi; qolgan tillar `Intl` da to'g'ri va tegilmaydi.
   */
  if (isUzLatn(locale)) return uzLatnDate(parsed);
  return format.dateTime(parsed, { dateStyle: "medium" });
}
