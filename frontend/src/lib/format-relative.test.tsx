import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it } from "vitest";

import { useRelativePast } from "./format-relative";
import messages from "../../messages/uz-Latn.json";

/*
 * =============================================================================
 * NISBIY VAQT — 260828 topilmasining darvozasi.
 *
 * ⛔⛔ BU TEST BRAUZER XATOSINI QAYTA ISHLAB CHIQARA OLMAYDI va shuni
 *     bilib turib yozilgan: `vitest` jsdom ostida NODE ning Intl'ini
 *     ishlatadi, u yerda `Intl.RelativeTimeFormat('uz-Latn')` TO'G'RI
 *     javob beradi. Chrome esa o'sha chaqiruvda «-12 h» qaytarardi va
 *     kamera qatorida aynan shu matn turardi.
 *
 *     Shuning uchun darvoza boshqa narsani qulflaydi: matn KATALOGDAN
 *     olinishi. Kimdir `Intl.RelativeTimeFormat` ga qaytsa, quyidagi
 *     kutilgan satrlar mos kelmay qoladi.
 * =============================================================================
 */

const HOZIR = new Date("2026-08-28T09:46:00+05:00");

function oldin(ms: number): Date {
  return new Date(HOZIR.getTime() - ms);
}

/** Hookni chaqirib natijani DOM'ga chiqaradigan eng kichik idish. */
function Namuna({ value }: { value: Date }) {
  const relativePast = useRelativePast();
  return <span data-testid="natija">{relativePast(value, HOZIR)}</span>;
}

function matn(value: Date): string {
  /*
   * ⚠ HAR CHAQIRUVDA TOZA DOM: `cleanup()` testlar ORASIDA ishlaydi,
   *   bitta test ichidagi ikkinchi `render` esa oldingisining yonига
   *   qo'shilardi va `getByTestId` «multiple elements» berardi.
   */
  document.body.innerHTML = "";
  render(
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      timeZone="Asia/Tashkent"
    >
      <Namuna value={value} />
    </NextIntlClientProvider>,
  );
  return screen.getByTestId("natija").textContent ?? "";
}

describe("useRelativePast", () => {
  it("bir daqiqagacha «hozirgina» deydi", () => {
    expect(matn(oldin(0))).toBe("hozirgina");
  });

  it("daqiqa, soat va kunni O'ZBEKCHA yozadi", () => {
    expect(matn(oldin(3 * 60_000))).toBe("3 daqiqa oldin");
    expect(matn(oldin(12 * 3_600_000))).toBe("12 soat oldin");
    expect(matn(oldin(3 * 86_400_000))).toBe("3 kun oldin");
  });

  it("RAQAMLI FALLBACK BERMAYDI — 260828 xatosining aynan shakli", () => {
    const natija = matn(oldin(12 * 3_600_000));
    expect(natija).not.toMatch(/^-?\d+\s*[hmd]$/u);
    expect(natija).not.toContain("-");
  });

  it("kelajakdagi paytni «hozirgina» qiladi, manfiy son EMAS", () => {
    /*
     * Agent va server soati bir necha soniyaga farq qilishi NORMAL
     * (CLAUDE.md §8: har kadrga uch xil vaqt yoziladi). «-1 daqiqa
     * oldin» foydalanuvchiga nosozlik bo'lib ko'rinardi.
     */
    expect(matn(new Date(HOZIR.getTime() + 30_000))).toBe("hozirgina");
  });
});
