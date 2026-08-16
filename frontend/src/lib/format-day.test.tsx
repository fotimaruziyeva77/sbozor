/**
 * ⛔ WR-07 — SANA-FAQAT QIYMAT VAQT MINTAQASIDAN MUSTAQIL O'QILADI.
 *
 * =============================================================================
 * ⛔⛔ NEGA BU SOF FUNKSIYA TESTI KOMPONENT TESTIDAN AJRATILGAN.
 *
 * Nosozlik ⛔ RENDER MASHINASIDA emas, ⛔ PARSE QOIDASIDA: `"2026-08-11
 * T00:00:00"` (ofsetsiz) satr ⛔ BRAUZERNING MAHALLIY mintaqasida talqin
 * qilinadi. Komponent testi esa `TZ` ni almashtira olmaydi — jarayon
 * mintaqasi bitta va u odatda AYNAN Toshkent, ya'ni nosozlik
 * ⛔ TASODIFAN to'g'ri ishlab, darvoza JIMGINA yashil bo'lardi.
 *
 * ⛔ SHUNING UCHUN DA'VO `Intl` NING `timeZone` ARGUMENTI USTIDAN
 *    yuritiladi: u jarayon mintaqasidan MUSTAQIL va o'nlab mintaqani bir
 *    testda o'lchaydi.
 * =============================================================================
 */
import { describe, expect, test } from "vitest";

import { isoDayToDate } from "@/lib/format-day";

const DAY = "2026-08-11";

/**
 * ⛔ QAMROV — `-11` DAN `+11` GACHA, VA CHEGARA OCHIQ AYTILADI.
 *
 * Yordamchi kunni ⛔ 12:00 UTC ga langarlaydi, ya'ni |ofset| < 12 bo'lgan
 * HAR mintaqada kalendar kuni AYNI qoladi. `+12`/`+13`/`+14` (Auckland,
 * Kiritimati) chegaradan TASHQARIDA va bu ⛔ YASHIRILMAYDI: mahsulot
 * O'zbekiston bozorlari uchun va u yerda ofset `+5`, o'zgarmas.
 */
const ZONES = [
  "Pacific/Midway", // -11
  "America/Anchorage", // -8
  "America/New_York", // -4
  "UTC",
  "Europe/Moscow", // +3
  "Asia/Tashkent", // +5 — mahsulotning O'Z mintaqasi
  "Asia/Bishkek", // +6 — Toshkentdan SHARQDA (WR-07 ning aynan holati)
  "Asia/Tokyo", // +9
  "Australia/Brisbane", // +10
  "Pacific/Norfolk", // +11
] as const;

/** `Date` -> `YYYY-MM-DD` AYNIQ mintaqada (`day-picker.tsx` naqshi). */
function calendarDayIn(timeZone: string, value: Date): string {
  return new Intl.DateTimeFormat("en-CA", {
    day: "2-digit",
    month: "2-digit",
    timeZone,
    year: "numeric",
  }).format(value);
}

describe("⛔ WR-07: kalendar kuni MINTAQADAN mustaqil", () => {
  test("⛔ o'nta mintaqaning HAMMASIDA kun AYNAN o'sha kun", () => {
    const parsed = isoDayToDate(DAY);
    expect(parsed).not.toBeNull();

    const shifted = ZONES.filter(
      (zone) => calendarDayIn(zone, parsed as Date) !== DAY,
    );

    /*
     * ⛔ TO'PLAM TENGLIGI, «bittasi to'g'rimi?» EMAS: bitta mintaqaga
     *   qadalgan da'vo AYNAN o'sha nosozlikni o'tkazib yuborardi
     *   (Toshkentda hamma narsa tasodifan to'g'ri ishlaydi).
     */
    expect(shifted).toEqual([]);
  });

  test("⛔ NAZORAT — YARIM TUNGA langarlangan shakl HAQIQATAN siljiydi", () => {
    /*
     * ⛔⛔ USIZ YUQORIDAGI DA'VO BO'SH-ROST BO'LARDI: agar `Intl` mintaqa
     *     argumentini e'tiborsiz qoldirsa, HAR shakl «to'g'ri» ko'rinardi.
     *     Bu test o'lchov asbobining O'ZI ishlayotganini isbotlaydi —
     *     yarim tunga langarlangan lahza manfiy ofsetli mintaqada
     *     ⛔ BIR KUN OLDIN chiziladi.
     */
    const midnightUtc = new Date(Date.UTC(2026, 7, 11, 0, 0, 0));

    expect(calendarDayIn("America/New_York", midnightUtc)).toBe("2026-08-10");
    /* ⛔ Va TUSHGA langarlangan lahza o'sha mintaqada ham siljimaydi. */
    expect(calendarDayIn("America/New_York", isoDayToDate(DAY) as Date)).toBe(DAY);
  });
});

describe("⛔ yaroqsiz kun — `null`, TO'QILGAN sana EMAS", () => {
  test("⛔ shakl ham, KALENDAR ham tekshiriladi", () => {
    /*
     * ⛔ SHAKL TEKSHIRUVI YETARLI EMAS: `2026-02-30` naqshga mos keladi,
     *   lekin MAVJUD EMAS (`isValidIsoDay` bilan aynan bir sabab).
     */
    for (const invalid of ["", "bekor", "2026-8-11", "2026-13-01", "2026-02-30"]) {
      expect(isoDayToDate(invalid)).toBeNull();
    }
  });

  test("⛔ ZAXIRA SANA YO'Q — `Date.now()` ham, epoxa ham qaytarilmaydi", () => {
    /*
     * ⛔ To'qilgan lahza ekranga O'LCHANGAN sana bo'lib chizilardi
     *   (05-14 darsi): «bugun» yozilgan qator nizoda BOSHQA kunni
     *   ko'rsatardi.
     */
    expect(isoDayToDate("bekor")).toBeNull();
    expect(isoDayToDate("bekor")).not.toBeInstanceOf(Date);
  });
});
