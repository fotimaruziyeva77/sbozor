/**
 * TREND O'QI — «CHIROYLI QADAM» HISOBI (260819).
 *
 * =============================================================================
 * ⛔⛔ BU TEST JONLI NUQSONDAN TUG'ILGAN.
 *
 *   O'q yorlig'i `Math.round(value / 10_000) * 10_000` bilan yozilardi.
 *   16 000 lik ustunda uchta chiziq 0 / 5 867 / 11 733 / 17 600 qiymatga
 *   ega bo'lib, yaxlitlashdan keyin ekranda shunday chiqdi:
 *
 *       20 000 · 10 000 · 10 000 · 0
 *
 *   Ikki xil BALANDLIKDAGI chiziq bir xil son bilan belgilangan — ya'ni
 *   o'q soxta. Bu hokim va tekshiruvchi ko'radigan ekran.
 *
 * ⛔ DA'VO: har chiziqning qiymati BUTUN va ular O'ZARO TENG oraliqda —
 *    ya'ni yorliqni yaxlitlash umuman kerak emas.
 * =============================================================================
 */
import { describe, expect, test } from "vitest";

import { niceMax } from "./revenue-trend";

const LINES = 3;

/** Chiziq qiymatlari — komponentdagi `(max * k) / GRID_LINES` bilan bir xil. */
function gridValues(peak: number): number[] {
  const max = niceMax(peak, LINES);
  return Array.from({ length: LINES + 1 }, (_, k) => (max * k) / LINES);
}

describe("niceMax", () => {
  test("nuqson qaytmaydi: 16 000 da yorliqlar TAKRORLANMAYDI", () => {
    const values = gridValues(16_000);

    expect(new Set(values).size).toBe(values.length);
    /* Eski xulq: [0, 5867, 11733, 17600] -> «0 · 10 000 · 10 000 · 20 000». */
    expect(values).toEqual([0, 6_000, 12_000, 18_000]);
  });

  test("har chiziq BUTUN son — yaxlitlash kerak emas", () => {
    for (const peak of [1, 7, 999, 16_000, 24_180_000, 1_234_567]) {
      for (const value of gridValues(peak)) {
        expect(Number.isInteger(value)).toBe(true);
      }
    }
  });

  test("shift har doim eng katta qiymatni QAMRAB oladi", () => {
    for (const peak of [1, 999, 16_000, 24_180_000, 1_234_567]) {
      expect(niceMax(peak, LINES)).toBeGreaterThanOrEqual(peak);
    }
  });

  test("bo'sh ma'lumot nolga bo'linishga olib kelmaydi", () => {
    expect(niceMax(0, LINES)).toBe(LINES);
    expect(niceMax(-5, LINES)).toBe(LINES);
    expect(niceMax(Number.NaN, LINES)).toBe(LINES);
  });

  test("qadam faqat odam o'qiydigan shakllardan (1·2·3·4·5·6·8·10)", () => {
    const allowed = [1, 2, 3, 4, 5, 6, 8, 10];
    for (const peak of [3, 37, 420, 6_400, 88_000, 950_000]) {
      const step = niceMax(peak, LINES) / LINES;
      const magnitude = 10 ** Math.floor(Math.log10(step));
      expect(allowed).toContain(step / magnitude);
    }
  });
});
