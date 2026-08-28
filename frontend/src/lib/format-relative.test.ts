import { describe, expect, it } from "vitest";

import { formatRelativePast } from "./format-relative";
import messages from "../../messages/uz-Latn.json";

/*
 * =============================================================================
 * NISBIY VAQT — 260828 topilmasining darvozasi.
 *
 * ⛔⛔ BU TEST BRAUZER XATOSINI QAYTA ISHLAB CHIQARA OLMAYDI va shuni
 *     bilib turib yozilgan: `vitest` NODE ning Intl'ini ishlatadi, u
 *     yerda `Intl.RelativeTimeFormat('uz-Latn')` TO'G'RI javob beradi.
 *     Chrome esa o'sha chaqiruvda «-12 h» qaytarardi.
 *
 *     Shuning uchun darvoza boshqa narsani qulflaydi: bizning
 *     funksiyamiz Intl'ga UMUMAN murojaat qilmasligi va matnni
 *     TARJIMA FAYLIDAN olishi. Intl qaytib kelsa, `t` chaqirilmay
 *     qoladi va pastdagi kutilgan matnlar mos kelmaydi.
 * =============================================================================
 */

/** `useTranslations()` ning shu test uchun yetarli o'rnini bosuvchisi. */
function t(key: string, values?: Record<string, number>): string {
  const [bolim, kalit] = key.split(".");
  const shablon = (messages as Record<string, Record<string, string>>)[bolim][
    kalit
  ];
  return shablon.replace(/\{(\w+)\}/gu, (_, nom: string) =>
    String(values?.[nom] ?? `{${nom}}`),
  );
}

const HOZIR = new Date("2026-08-28T09:46:00+05:00");

function oldin(ms: number): Date {
  return new Date(HOZIR.getTime() - ms);
}

describe("formatRelativePast", () => {
  it("bir daqiqagacha «hozirgina» deydi", () => {
    expect(formatRelativePast(oldin(0), HOZIR, t)).toBe("hozirgina");
    expect(formatRelativePast(oldin(59_000), HOZIR, t)).toBe("hozirgina");
  });

  it("daqiqa, soat va kunni O'ZBEKCHA yozadi", () => {
    expect(formatRelativePast(oldin(3 * 60_000), HOZIR, t)).toBe(
      "3 daqiqa oldin",
    );
    expect(formatRelativePast(oldin(12 * 3_600_000), HOZIR, t)).toBe(
      "12 soat oldin",
    );
    expect(formatRelativePast(oldin(3 * 86_400_000), HOZIR, t)).toBe(
      "3 kun oldin",
    );
  });

  it("RAQAMLI FALLBACK BERMAYDI — 260828 xatosining aynan shakli", () => {
    const natija = formatRelativePast(oldin(12 * 3_600_000), HOZIR, t);
    expect(natija).not.toMatch(/^-?\d+\s*[hmd]$/u);
    expect(natija).not.toContain("-");
  });

  it("kelajakdagi paytni «hozirgina» qiladi, manfiy son EMAS", () => {
    /*
     * Agent va server soati bir necha soniyaga farq qilishi NORMAL
     * (CLAUDE.md §8: uch xil vaqt yoziladi). «-1 daqiqa oldin» esa
     * foydalanuvchiga nosozlik bo'lib ko'rinardi.
     */
    expect(formatRelativePast(new Date(HOZIR.getTime() + 30_000), HOZIR, t)).toBe(
      "hozirgina",
    );
  });
});
