/**
 * ⛔ DAFTAR IMPORTI — KUN TANLAGICHI (§10.2) VA DL-6 TASDIG'I (§14.8).
 *
 * =============================================================================
 * ⛔⛔ 1. MAKSIMUM KUN — ⛔ KECHA, `/billing` DAGI BUGUN EMAS.
 *
 * Bugungi tizim summasi HALI YOPILMAGAN (`daily_charges` D+1 04:10 da
 * tug'iladi) va daftar ham kun oxirida yig'iladi. «Bugun» ni solishtirish
 * ⛔ HAR DOIM farq ko'rsatardi va uchala sinf ham ⛔ SOXTA bo'lardi —
 * ya'ni ekran har kuni «bozorda 300 ta nomuvofiqlik» deb yolg'on
 * gapirardi va parallel rejim birinchi kunidayoq ishonchdan chiqardi.
 *
 * ⛔ Shuning uchun `useBillingDay()` TO'G'RIDAN-TO'G'RI qayta
 *    ishlatilmaydi: uning maksimumi BUGUN.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 2. ALMASHTIRISH — AYNAN BITTA TASDIQDAN O'TADI.
 *
 * Daftar BOR bo'lgan kunga ikkinchi fayl yuborish eski qatorlarni
 * ⛔ ALMASHTIRADI (D-17). Tasdiqsiz bu «yuklash» tugmasini tasodifan
 * bosish bilan sodir bo'lardi. ⛔ Lekin `level: 2` ham ISHLATILMAYDI: bu
 * ⛔ KUNLIK operatsion amal va matn yozdirish uni har kuni jazolardi.
 *
 * ⛔ Daftar YO'Q bo'lganda dialog UMUMAN ochilmaydi — yo'qotiladigan
 *    narsa yo'q va ortiqcha bosish kunlik ishni sekinlashtirardi.
 * =============================================================================
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { RenderResult } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { NuqsTestingAdapter } from "nuqs/adapters/testing";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

const apiClientMock = vi.hoisted(() => ({ apiFetch: vi.fn() }));
const toastMock = vi.hoisted(() => ({ success: vi.fn(), error: vi.fn() }));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiClientMock.apiFetch };
});

vi.mock("sonner", () => ({ toast: toastMock }));

import messages from "../../../messages/uz-Latn.json";
import {
  CompareDayPicker,
  LedgerImport,
  LEDGER_FILE_INPUT_ID,
} from "@/components/reports/ledger-import";
import { ApiError } from "@/lib/api-client";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const TIME_ZONE = "Asia/Tashkent";
const MARKET_ID = "11111111-1111-4111-8111-111111111111";

/** ⛔ Yagona lahza — literal sana YO'Q, kutilmalar undan HOSILA. */
const TODAY = "2026-10-15";
const YESTERDAY = "2026-10-14";
const CHOSEN_DAY = "2026-10-10";

const LOADED_ROWS = 42;

function freezeClock(): Date {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(`${TODAY}T12:00:00+05:00`));
  return new Date();
}

function comparePayload(hasLedger: boolean) {
  return {
    day: CHOSEN_DAY,
    has_ledger: hasLedger,
    rows: [],
    ledger_over_count: 0,
    system_over_count: 0,
    ai_mismatch_count: 0,
    matched_count: 0,
  };
}

function openSession() {
  clearSession();
  setSession({
    accessToken: "t",
    markets: [],
    principal: {
      userId: "33333333-3333-4333-8333-333333333333",
      phone: "+998900000000",
      fullName: "Test Admin",
      roles: ["market_admin"],
      marketId: MARKET_ID,
      marketName: "Karmana markaziy bozori",
      isPlatformAdmin: false,
      locale: "uz-Latn",
      mustChangePassword: false,
    },
  });
}

beforeEach(() => {
  vi.resetAllMocks();
  openSession();
});

afterEach(() => {
  vi.useRealTimers();
});

type Options = {
  hasLedger?: boolean;
  uploadFails?: unknown;
  searchParams?: string;
};

function renderPanel(
  node: React.ReactNode,
  { hasLedger = false, uploadFails, searchParams }: Options = {},
): RenderResult {
  const now = freezeClock();

  apiClientMock.apiFetch.mockImplementation((path: string, init?: unknown) => {
    const method = (init as { method?: string } | undefined)?.method;
    if (path.startsWith("/reports/compare/ledger") && method === "POST") {
      if (uploadFails !== undefined) return Promise.reject(uploadFails);
      return Promise.resolve({
        day: CHOSEN_DAY,
        rows: LOADED_ROWS,
        replaced: hasLedger,
      });
    }
    if (path.startsWith("/reports/compare")) {
      return Promise.resolve(comparePayload(hasLedger));
    }
    return Promise.reject(new Error(`kutilmagan marshrut: ${path}`));
  });

  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  return render(
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      now={now}
      timeZone={TIME_ZONE}
    >
      <NuqsTestingAdapter searchParams={searchParams ?? `?day=${CHOSEN_DAY}`}>
        <QueryClientProvider client={client}>
          <AuthProvider>{node}</AuthProvider>
        </QueryClientProvider>
      </NuqsTestingAdapter>
    </NextIntlClientProvider>,
  );
}

function dayInput(view: RenderResult): HTMLInputElement {
  const input = view.container.querySelector('input[type="date"]');
  if (input === null) throw new Error("kun tanlagichi topilmadi");
  return input as HTMLInputElement;
}

function fileInput(view: RenderResult): HTMLInputElement {
  const input = view.container.querySelector(`#${LEDGER_FILE_INPUT_ID}`);
  if (input === null) throw new Error("fayl maydoni topilmadi");
  return input as HTMLInputElement;
}

function chooseFile(view: RenderResult): void {
  fireEvent.change(fileInput(view), {
    target: { files: [new File(["x"], "daftar.xlsx")] },
  });
}

function uploadButton(): HTMLElement {
  return screen.getByRole("button", { name: messages.compare.ledgerUpload });
}

/** POST bo'lgan `apiFetch` chaqiruvlari soni. */
function uploadCalls(): number {
  return apiClientMock.apiFetch.mock.calls.filter(
    (call) => (call[1] as { method?: string } | undefined)?.method === "POST",
  ).length;
}

/* -------------------------------------------------------------------------- */
/* §10.2 — ⛔ MAKSIMUM KUN KECHA                                              */
/* -------------------------------------------------------------------------- */

describe("⛔ kun tanlagichi — maksimum KECHA (§10.2)", () => {
  test("⛔ `max` atributi KECHA, ⛔ bugun EMAS", () => {
    const view = renderPanel(<CompareDayPicker />);

    expect(dayInput(view).getAttribute("max")).toBe(YESTERDAY);
    /*
     * ⛔ NAZORAT: da'vo «bugun emas» ni ALOHIDA aytadi. Tenglik yolg'iz
     *   qolsa, sana arifmetikasi buzilib ikkalasi bir xil bo'lganda ham
     *   yashil qolardi.
     */
    expect(dayInput(view).getAttribute("max")).not.toBe(TODAY);
  });

  test("⛔ `?day=bugun` STANDARTGA (kecha) tushadi", () => {
    const view = renderPanel(<CompareDayPicker />, {
      searchParams: `?day=${TODAY}`,
    });

    expect(dayInput(view).value).toBe(YESTERDAY);
  });

  test("⛔ nomlangan sabab EKRANDA — «rang yo'q, sabab bor» (§13.4)", () => {
    const view = renderPanel(<CompareDayPicker />);

    expect(view.container.textContent).toContain(messages.compare.maxDayHint);
  });
});

/* -------------------------------------------------------------------------- */
/* §14.8 / DL-6 — ⛔ ALMASHTIRISH AYNAN BITTA TASDIQDAN                       */
/* -------------------------------------------------------------------------- */

describe("⛔ DL-6 — daftarni almashtirish tasdig'i", () => {
  test("⛔ daftar BOR: bosish so'rov YUBORMAYDI, dialog ochiladi", async () => {
    const view = renderPanel(<LedgerImport />, { hasLedger: true });

    await waitFor(() => {
      expect(view.container.textContent).toContain(
        messages.compare.ledgerPresent,
      );
    });

    chooseFile(view);
    fireEvent.click(uploadButton());

    expect(
      await screen.findByText(messages.compare.ledgerReplaceTitle),
    ).toBeInTheDocument();

    /* ⛔ ENG QIMMAT DA'VO: tasdiqdan OLDIN hech nima yozilmaydi. */
    expect(uploadCalls()).toBe(0);
  });

  test("⛔ tasdiqlangandan keyin AYNAN BITTA so'rov ketadi", async () => {
    const view = renderPanel(<LedgerImport />, { hasLedger: true });

    await waitFor(() => {
      expect(view.container.textContent).toContain(
        messages.compare.ledgerPresent,
      );
    });

    chooseFile(view);
    fireEvent.click(uploadButton());
    fireEvent.click(
      await screen.findByRole("button", {
        name: messages.compare.ledgerReplaceConfirm,
      }),
    );

    await waitFor(() => {
      expect(uploadCalls()).toBe(1);
    });
  });

  test("⛔ daftar YO'Q: dialog UMUMAN ochilmaydi", async () => {
    const view = renderPanel(<LedgerImport />, { hasLedger: false });

    await waitFor(() => {
      expect(view.container.textContent).toContain(
        messages.compare.ledgerMissing,
      );
    });

    chooseFile(view);
    fireEvent.click(uploadButton());

    await waitFor(() => {
      expect(uploadCalls()).toBe(1);
    });
    expect(
      screen.queryByText(messages.compare.ledgerReplaceTitle),
    ).toBeNull();
  });

  test("⛔ muvaffaqiyatda TOAST — fazadagi YAGONA toast turi (§14.7)", async () => {
    const view = renderPanel(<LedgerImport />, { hasLedger: false });

    await waitFor(() => {
      expect(view.container.textContent).toContain(
        messages.compare.ledgerMissing,
      );
    });

    chooseFile(view);
    fireEvent.click(uploadButton());

    await waitFor(() => {
      expect(toastMock.success).toHaveBeenCalledWith(
        `Daftar yuklandi: ${LOADED_ROWS} qator`,
      );
    });
  });
});

/* -------------------------------------------------------------------------- */
/* §10.3 — ⛔ 422 XATOLARI RO'YXAT BO'LIB, UCH TILDA                          */
/* -------------------------------------------------------------------------- */

describe("⛔ 422 — all-or-nothing va TARJIMA QILINGAN qator xatolari", () => {
  test("⛔ daftar kodlari server matnini emas, TARJIMANI chizadi", async () => {
    const view = renderPanel(<LedgerImport />, {
      hasLedger: false,
      uploadFails: new ApiError(422, "validation_failed", {
        detail: "validation_failed",
        errors: [
          { row: 4, code: "ledger_stall_unknown", message: "server matni" },
        ],
        error_counts: { ledger_stall_unknown: 1 },
      }),
    });

    await waitFor(() => {
      expect(view.container.textContent).toContain(
        messages.compare.ledgerMissing,
      );
    });

    chooseFile(view);
    fireEvent.click(uploadButton());

    /* ⛔ D-14: «HECH NARSA SAQLANMADI» jumlasi BIRINCHI, DOIM. */
    expect(
      await screen.findByText(messages.import.nothingSaved),
    ).toBeInTheDocument();

    /*
     * ⛔ SERVER MATNI EKRANGA CHIQMAYDI (07 D-04): u FAQAT uz-Latn va
     *   rus tilidagi admin uni tarjimasiz o'qirdi.
     */
    expect(view.container.textContent).toContain(
      messages.import.errors.ledger_stall_unknown,
    );
    expect(view.container.textContent).not.toContain("server matni");
  });

  test("⛔ qatorga aloqasi YO'Q xato — SABAB + NIMA QILISH (§14.9)", async () => {
    const view = renderPanel(<LedgerImport />, {
      hasLedger: false,
      uploadFails: new ApiError(409, "day_locked", { detail: "day_locked" }),
    });

    await waitFor(() => {
      expect(view.container.textContent).toContain(
        messages.compare.ledgerMissing,
      );
    });

    chooseFile(view);
    fireEvent.click(uploadButton());

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain(
      messages.reports.errorCause.ledger_day_locked,
    );
    /* ⛔ Yolg'iz sabab foydalanuvchini boshi berk ko'chaga qo'yardi. */
    expect(alert.textContent).toContain(
      messages.reports.errorFix.ledger_day_locked,
    );
  });
});

/* -------------------------------------------------------------------------- */
/* §13.3 / §6.1 — ⛔ FAZADAGI YAGONA AKSENT VA U 44 px                        */
/* -------------------------------------------------------------------------- */

describe("⛔ `[Daftarni yuklash]` — fazadagi YAGONA aksent (§13.3)", () => {
  test("⛔ aksent fon + `size=\"lg\"`; shablon tugmasi esa AKSENTSIZ", async () => {
    const view = renderPanel(<LedgerImport />, { hasLedger: false });

    await waitFor(() => {
      expect(view.container.textContent).toContain(
        messages.compare.ledgerMissing,
      );
    });

    const submit = uploadButton();
    expect(submit.className).toContain("bg-accent");
    /* ⛔ 44 px barmoq nishoni: bozor admini uni TELEFONDA ham bosadi. */
    expect(submit.className).toContain("min-h-11");

    const template = screen.getByRole("button", {
      name: messages.compare.ledgerTemplate,
    });
    expect(template.className).not.toContain("bg-accent");
  });
});
