/**
 * EKSPORT TUGMASI — ⛔ YAGONA YUKLAB OLISH YO'LI VA INLINE XATO (§12.2, §13.3).
 *
 * =============================================================================
 * ⛔⛔ NEGA BU TEST BOR: NOSOZLIK JIM BO'LADI.
 *
 * Access token XOTIRADA yashaydi va so'rov SARLAVHASIDA ketadi. Brauzer
 * o'zi boshlaydigan yuklab olish esa ⛔ TOKENSIZ ketadi va `401` oladi —
 * brauzer 401 javob TANASINI `revenue.xlsx` nomi bilan diskka SAQLAYDI.
 * Foydalanuvchi «fayl yuklandi» deb o'ylaydi, Excel «fayl buzilgan»
 * deydi va xato ⛔ HECH QAYERDA ko'rinmaydi (M-7, T-08-35).
 *
 * Shuning uchun bu yerda ikki xil da'vo bor va ikkalasi ham kerak:
 *   • STATIK — taqiqlangan tokenlar manbada yo'q (G-38(a), 08-15 da);
 *   • XULQIY — bu fayl: bosish AYNAN `downloadReport` ga boradi.
 *
 * ⛔ XATO TOASTDA EMAS, INLINE. Toast g'oyib bo'ladi va foydalanuvchi
 *    tugmani QAYTA-QAYTA bosardi — ya'ni og'ir eksport so'rovi bir necha
 *    marta serverga urardi (T-08-38).
 * =============================================================================
 */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { beforeEach, describe, expect, test, vi } from "vitest";

const reportQueriesMock = vi.hoisted(() => ({
  downloadCompareReport: vi.fn(),
  downloadReport: vi.fn(),
}));

vi.mock("@/lib/report-queries", () => reportQueriesMock);

import messages from "../../../messages/uz-Latn.json";
import { ExportButton } from "@/components/reports/export-button";
import { ApiError } from "@/lib/api-client";

const PERIOD = { from: "2026-07-17", to: "2026-08-15" } as const;

beforeEach(() => {
  vi.resetAllMocks();
});

function renderButton() {
  const view = render(
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      timeZone="Asia/Tashkent"
    >
      <ExportButton kind="revenue" period={PERIOD} />
    </NextIntlClientProvider>,
  );

  return {
    button: screen.getByRole("button", { name: messages.reports.export }),
    view,
  };
}

/* -------------------------------------------------------------------------- */
/* (f) YAGONA YO'L — BOSISH `downloadReport` GA BORADI                        */
/* -------------------------------------------------------------------------- */

describe("⛔ yuklab olishning YAGONA yo'li", () => {
  test("bosilganda `downloadReport(kind, period)` chaqiriladi", async () => {
    reportQueriesMock.downloadReport.mockResolvedValue(undefined);

    const { button } = renderButton();
    fireEvent.click(button);

    await waitFor(() =>
      expect(reportQueriesMock.downloadReport).toHaveBeenCalledTimes(1),
    );

    /*
     * ⛔ ARGUMENTLAR HAM O'LCHANADI: davrsiz chaqiruv fayl ichidagi
     *   raqamni hech nimaga bog'lanmagan holda qoldirardi (§1.2 qoida 2)
     *   va uni «chaqirildi» da'vosi KO'RMASDI.
     */
    expect(reportQueriesMock.downloadReport).toHaveBeenCalledWith(
      "revenue",
      PERIOD,
    );
  });

  test("muvaffaqiyatda hech qanday xato matni chizilmaydi", async () => {
    reportQueriesMock.downloadReport.mockResolvedValue(undefined);

    const { button, view } = renderButton();
    fireEvent.click(button);

    await waitFor(() =>
      expect(reportQueriesMock.downloadReport).toHaveBeenCalledTimes(1),
    );

    /*
     * ⛔ SALBIY NAZORAT: xato bloki muvaffaqiyatda TUG'ILMAYDI. Busiz (h)
     *   testi «blok DOIM chizilgan» holatida ham yashil qolardi.
     */
    expect(view.container.querySelectorAll('[role="alert"]').length).toBe(0);
  });
});

/* -------------------------------------------------------------------------- */
/* (h) XATO — INLINE, SABAB + TUZATISH                                        */
/* -------------------------------------------------------------------------- */

describe("⛔ xato INLINE ko'rsatiladi (toast EMAS)", () => {
  test("`report_too_large` da SABAB va TUZATISH matni tugma yonida chiziladi", async () => {
    reportQueriesMock.downloadReport.mockRejectedValue(
      new ApiError(413, "report_too_large"),
    );

    const { button } = renderButton();
    fireEvent.click(button);

    /*
     * ⚠ QIDIRUV ROLGA TAYANMAYDI — matn `getByText` bilan topiladi. Bu
     *   ATAYIN: da'vo matnning KO'RINISHI haqida, uning e'lon
     *   mexanizmi haqida emas.
     */
    await waitFor(() =>
      expect(
        screen.getByText(messages.reports.errorCause.report_too_large),
      ).toBeInTheDocument(),
    );

    /*
     * ⛔ TUZATISH MATNI HAM SHART (D-02): yolg'iz sabab direktorni boshi
     *   berk ko'chaga qo'yardi — u nima bo'lganini biladi, lekin keyingi
     *   qadamni bilmaydi.
     */
    expect(
      screen.getByText(messages.reports.errorFix.report_too_large),
    ).toBeInTheDocument();
  });

  test("NOMA'LUM kod zaxira `report_export_failed` juftligiga tushadi", async () => {
    reportQueriesMock.downloadReport.mockRejectedValue(
      new ApiError(500, "kafka_broker_unreachable"),
    );

    const { button } = renderButton();
    fireEvent.click(button);

    /*
     * ⛔ XOM ISTISNO MATNI HECH QACHON EKRANGA CHIQMAYDI [MEROS: 07 D-04].
     *   Noma'lum kod nomlangan zaxira juftligiga tushadi — ekranda
     *   `kafka_broker_unreachable` ko'rinishi mumkin emas.
     */
    await waitFor(() =>
      expect(
        screen.getByText(messages.reports.errorCause.report_export_failed),
      ).toBeInTheDocument(),
    );

    expect(screen.queryByText(/kafka_broker_unreachable/u)).toBeNull();
  });
});

/* -------------------------------------------------------------------------- */
/* (i) YUKLANISH — `aria-busy`, matn O'ZGARMAYDI                              */
/* -------------------------------------------------------------------------- */

describe("yuklanish holati", () => {
  test("⛔ `aria-busy=\"true\"` qo'yiladi va tugma MATNI o'zgarmaydi", async () => {
    let release: (() => void) | null = null;
    reportQueriesMock.downloadReport.mockReturnValue(
      new Promise<void>((resolve) => {
        release = resolve;
      }),
    );

    const { button } = renderButton();
    fireEvent.click(button);

    await waitFor(() =>
      expect(button.getAttribute("aria-busy")).toBe("true"),
    );

    /*
     * ⛔ MATN O'ZGARMASLIGI DA'VOSI — o'lcham sakramasligi uchun (§12.2).
     *   «Tayyorlanmoqda» ga almashtirilsa tugma torayardi va yonidagi
     *   uchta tugma SIYLARDI — sahifada to'rttasi bor (§12.1).
     */
    expect(button.textContent).toContain(messages.reports.export);

    release?.();

    await waitFor(() => expect(button.getAttribute("aria-busy")).toBe("false"));
  });
});
