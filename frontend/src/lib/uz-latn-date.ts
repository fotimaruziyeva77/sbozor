/*
 * =============================================================================
 * O'ZBEK LOTIN SANASI — ⛔ BRAUZER BERMAYDIGAN MA'LUMOTNING O'RNI.
 *
 * ⛔⛔ NIMANI TUZATADI (o'lchangan 2026-08-18, jonli Chrome'da):
 *
 *   new Intl.DateTimeFormat("uz-Latn", { dateStyle: "medium" }).format(d)
 *     -> "2026 M08 15"          ⛔ CLDR ILDIZ shabloni
 *
 *   Ayni chaqiruv `uz-Cyrl` da "15 авг, 2026", `ru` da "15 авг. 2026 г." —
 *   ya'ni nosozlik FAQAT o'zbek LOTIN yozuvida va u bizning ASOSIY tilimiz.
 *   Aniq shakl ham yordam bermaydi: { month: "long" } ham "M08" beradi,
 *   chunki brauzer ICU'sida bu yozuv uchun oy nomlari UMUMAN yo'q.
 *   Node'ning to'liq ICU'si ularni biladi — shuning uchun nosozlik SSR'da
 *   ko'rinmay, brauzerda ko'rinadi.
 *
 * ⛔ Shuning uchun oy nomlari SHU YERDA, kodda. Bu tarjima EMAS —
 *    brauzerda yetishmayotgan CLDR jadvalining o'rni. Tarjima katalogiga
 *    qo'yilsa, uchala tilda takrorlanib, ikkitasida hech qachon
 *    ishlatilmasdi va drift manbai bo'lardi.
 *
 * ⛔ FAQAT `uz-Latn` uchun. Qolgan tillar `Intl` da to'g'ri ishlaydi va
 *    ularga tegilmaydi — ikkinchi haqiqat manbai yaratmaymiz.
 * =============================================================================
 */

/** Ilova tili o'zbek lotin yozuvidami. */
export function isUzLatn(locale: string): boolean {
  return locale === "uz-Latn" || locale === "uz";
}

/**
 * Oy nomlari — bosh harfsiz (o'zbek tilida oy nomi jumla o'rtasida kichik
 * harf bilan yoziladi). Indeks `Date#getUTCMonth()` bilan bir xil: 0 = yanvar.
 */
const MONTHS = [
  "yanvar",
  "fevral",
  "mart",
  "aprel",
  "may",
  "iyun",
  "iyul",
  "avgust",
  "sentabr",
  "oktabr",
  "noyabr",
  "dekabr",
] as const;

/**
 * `2026-08-18` -> «18-avgust, 2026».
 *
 * ⛔ UTC qismlari o'qiladi: chaqiruvchi kunni TUSHGA langarlangan lahza
 *    sifatida beradi (`format-day.ts` sharti), ya'ni mahalliy mintaqa
 *    kunni surib yubormaydi.
 */
export function uzLatnDate(date: Date): string {
  const month = MONTHS[date.getUTCMonth()];
  return `${date.getUTCDate()}-${month}, ${date.getUTCFullYear()}`;
}

/**
 * Hafta kunlari — `Date#getUTCDay()` indeksi bilan: 0 = yakshanba.
 *
 * ⛔ Sabab oy jadvali bilan BIR XIL: brauzer ICU'sida o'zbek LOTIN
 *    yozuvi uchun hafta kunlari YO'Q va `{ weekday: "long" }` ildiz
 *    shabloniga tushib INGLIZCHA qisqartma («Tue») beradi. Bu jonli
 *    o'lchandi (2026-08-18, nazoratchi ekranida).
 */
const WEEKDAYS = [
  "yakshanba",
  "dushanba",
  "seshanba",
  "chorshanba",
  "payshanba",
  "juma",
  "shanba",
] as const;

/** `2026-08-18` -> «seshanba». Chaqiruvchi kunni TUSHGA langarlaydi. */
export function uzLatnWeekday(date: Date): string {
  return WEEKDAYS[date.getUTCDay()] ?? "";
}

/**
 * Sana va vaqt matnlarini birlashtiradi.
 *
 * ⛔ Ajratgich SHU YERDA, BIR MARTA: `uzLatnDateTime()` ham,
 *    `format-day.ts` dagi `formatInstant()` ham shu funksiyaga keladi,
 *    aks holda bir ekranda `·`, boshqasida `,` paydo bo'lardi.
 */
export function joinUzLatnDateTime(dateText: string, timeText: string): string {
  return `${dateText} · ${timeText}`;
}

/** `2026-08-18 09:41` -> «18-avgust, 2026 · 09:41» (vaqt chaqiruvchidan). */
export function uzLatnDateTime(date: Date, timeText: string): string {
  return joinUzLatnDateTime(uzLatnDate(date), timeText);
}

/**
 * LAHZA (timestamp) -> «18-avgust, 2026», ⛔ BERILGAN MINTAQADA.
 *
 * =============================================================================
 * ⛔⛔ NEGA `uzLatnDate()` BU YERDA YARAMAYDI.
 *
 * `uzLatnDate()` UTC qismlarini o'qiydi va bu KUN satri uchun to'g'ri
 * (`2026-08-18` -> UTC tush). Lekin `created_at` kabi LAHZA uchun u
 * xato: Toshkent UTC+5, ya'ni `2026-08-18T20:30:00Z` mahalliy vaqtda
 * ALLAQACHON 19-avgust. UTC o'qilsa ekranda «18-avgust» chiqib,
 * yonidagi `Intl` chizgan vaqt «01:30» bo'lardi — bir qatorda ikki
 * xil kun.
 *
 * ⛔ Oy raqami `Intl` dan `en-US` va RAQAMLI qismlar bilan olinadi:
 *    raqamlar hamma locale'da bir xil, ya'ni bu yerda CLDR'ning
 *    o'zbekcha jadvalidan HECH NARSA so'ralmaydi — oy NOMI baribir
 *    yuqoridagi o'z jadvalimizdan qo'yiladi.
 * =============================================================================
 */
export function uzLatnDateInZone(
  date: Date,
  /*
   * ⛔ `undefined` — RUXSAT ETILGAN va u `Intl` ga SHUNDAYLIGICHA
   *    uzatiladi: o'shanda tizim mintaqasi olinadi, ya'ni xulq
   *    `format.dateTime()` niki bilan BIR XIL. Bu yerda o'zimizcha
   *    "Asia/Tashkent" qo'yilsa, ilova sozlamasi o'zgargan kuni
   *    sana yonidagi vaqtdan AJRALIB ketardi.
   */
  timeZone: string | undefined,
): string {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone,
    year: "numeric",
    month: "numeric",
    day: "numeric",
  }).formatToParts(date);

  const pick = (type: "year" | "month" | "day"): string =>
    parts.find((part) => part.type === type)?.value ?? "";

  const monthIndex = Number(pick("month")) - 1;
  const month = MONTHS[monthIndex];
  /* Mintaqa noma'lum bo'lsa `Intl` otadi; oy topilmasa xom qiymatga qaytmaymiz. */
  if (month === undefined) return uzLatnDate(date);

  return `${Number(pick("day"))}-${month}, ${pick("year")}`;
}
