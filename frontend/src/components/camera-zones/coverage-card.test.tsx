/**
 * QAMROV KARTASI — D-22 NING KO'RINADIGAN SHAKLI.
 *
 * =============================================================================
 * BU FAYLNING MARKAZIY DA'VOSI:
 *
 *   ⛔ UCHALA SON HAM NOL BO'LGANDA HAM RENDER BO'LADI.
 *
 *   `coverage-warning.tsx` (4-faza) nol bo'lganda UMUMAN chizilmaydi va
 *   u to'g'ri edi — u OGOHLANTIRISH. Bu esa HISOBOT: «qamrovsiz rasta:
 *   0» degan qator adminning savoliga («hammasini belgilab bo'ldimmi?»)
 *   aynan JAVOB beradi. Kartani nol holatda yashirish o'sha savolni
 *   javobsiz qoldirardi.
 *
 *   ⚠ 05-06 ning S4 SABOTAJI AYNAN SHU YERDA TAKRORLANMASLIGI KERAK:
 *     «uchala son qaytadi» degan test buzilgan `uncovered` ni USHLAY
 *     OLMAYDI, chunki nol qiymat uni TRIVIAL qanoatlantiradi. Shuning
 *     uchun bu yerda IKKI fixture bor — nolli VA nolsiz — va nolsizida
 *     aynan `uncovered` ning QIYMATI o'qiladi.
 *
 * ⛔ «BO'SH» SO'ZI D-22 NING MATN DARVOZASI (G-15) va u
 *    `scripts/zone-copy.test.mjs` da yashaydi. Bu yerda esa UNING
 *    IKKINCHI YARMI o'lchanadi: karta haqiqatan O'SHA kalitlarni
 *    ishlatadimi. Darvoza matnni tekshiradi, bu test uning EKRANGA
 *    yetib borishini.
 * =============================================================================
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

const apiClientMock = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiClientMock.apiFetch };
});

import messages from "../../../messages/uz-Latn.json";
import { CoverageCard } from "@/components/camera-zones/coverage-card";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const MARKET_ID = "11111111-1111-4111-8111-111111111111";

let client: QueryClient;

function seedSession(): void {
  setSession({
    accessToken: "test-access-token",
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
    markets: [],
  });
}

function renderCard(children: ReactNode = <CoverageCard />) {
  return render(
    <QueryClientProvider client={client}>
      <AuthProvider>
        <NextIntlClientProvider
          locale="uz-Latn"
          messages={messages}
          timeZone="Asia/Tashkent"
        >
          {children}
        </NextIntlClientProvider>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.resetAllMocks();
  clearSession();
  seedSession();
  client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
});

afterEach(() => {
  client.clear();
  clearSession();
});

/* ------------------------------------------------------------------------- */

describe("⛔ nol — NATIJA, uning yo'qligi emas", () => {
  test("`uncovered === 0` bo'lganda ham KARTA RENDER BO'LADI", async () => {
    apiClientMock.apiFetch.mockResolvedValue({
      covered: 258,
      uncovered: 0,
      cameras_without_zones: 0,
    });

    renderCard();

    await screen.findByText(messages.cameraZones.coverageTitle);

    // Uchala YORLIQ ham joyida.
    expect(screen.getByText(messages.cameraZones.covered)).toBeInTheDocument();
    expect(screen.getByText(messages.cameraZones.uncovered)).toBeInTheDocument();
    expect(
      screen.getByText(messages.cameraZones.camerasWithoutZones),
    ).toBeInTheDocument();

    // Uchala SON ham: 258 + ikkita nol.
    expect(screen.getByText("258")).toBeInTheDocument();
    expect(screen.getAllByText("0")).toHaveLength(2);
  });

  test("nol holatda ijobiy xulosa QO'SHILADI (sonlar O'RNIGA emas)", async () => {
    apiClientMock.apiFetch.mockResolvedValue({
      covered: 12,
      uncovered: 0,
      cameras_without_zones: 0,
    });

    renderCard();

    await screen.findByText(messages.cameraZones.allCovered);
    // Xulosa sonlarni ALMASHTIRMAYDI — «12» hamon ekranda.
    expect(screen.getByText("12")).toBeInTheDocument();
  });
});

describe("⚠ nolsiz fixture — S4 sinfidagi trivial yashillikning oldi olinadi", () => {
  test("`uncovered` ning QIYMATI o'qiladi va sabab jumlasi chiqadi", async () => {
    apiClientMock.apiFetch.mockResolvedValue({
      covered: 258,
      uncovered: 42,
      cameras_without_zones: 3,
    });

    renderCard();

    await screen.findByText("42");
    expect(screen.getByText("258")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();

    /*
     * ⚠ SABAB JUMLASI FAQAT NOLSIZ HOLATDA: nol qamrovsiz rastada
     *   «ular haqida ma'lumot yig'ilmaydi» jumlasi hech kimga tegishli
     *   bo'lmasdi.
     */
    expect(
      screen.getByText(messages.cameraZones.uncoveredWhy),
    ).toBeInTheDocument();
    // Va ijobiy xulosa BU YERDA yo'q.
    expect(screen.queryByText(messages.cameraZones.allCovered)).toBeNull();
  });

  test("nol qamrovsiz rastada sabab jumlasi CHIQMAYDI (nazorat)", async () => {
    apiClientMock.apiFetch.mockResolvedValue({
      covered: 258,
      uncovered: 0,
      cameras_without_zones: 0,
    });

    renderCard();

    await screen.findByText(messages.cameraZones.coverageTitle);
    expect(screen.queryByText(messages.cameraZones.uncoveredWhy)).toBeNull();
  });
});

describe("semantika va jonli hudud", () => {
  test("`<dl>` — yorliq va son DASTURIY juftlik", async () => {
    apiClientMock.apiFetch.mockResolvedValue({
      covered: 5,
      uncovered: 1,
      cameras_without_zones: 0,
    });

    const { container } = renderCard();
    await screen.findByText(messages.cameraZones.coverageTitle);

    expect(container.querySelector("dl")).not.toBeNull();
    expect(container.querySelectorAll("dt")).toHaveLength(3);
    // Uchta son + bitta sabab jumlasi = to'rtta `<dd>`.
    expect(container.querySelectorAll("dd")).toHaveLength(4);
  });

  test("⚠ `role='status'`, `role='alert'` EMAS (§13.6)", async () => {
    apiClientMock.apiFetch.mockResolvedValue({
      covered: 5,
      uncovered: 1,
      cameras_without_zones: 0,
    });

    const { container } = renderCard();
    await screen.findByText(messages.cameraZones.coverageTitle);

    /*
     * Bu sahifa yuklanganda MAVJUD BO'LGAN holat, yangi hodisa emas.
     * `alert` uni har yuklanishda qayta o'qitib, admin uni eshitmay
     * qo'yardi (`coverage-warning.tsx` da o'rnatilgan qaror).
     */
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(container.querySelector("[role='alert']")).toBeNull();
  });

  test("⚠ SARIQ MATN EMAS — tint `bg-warning/20 text-text` (§10.2)", async () => {
    apiClientMock.apiFetch.mockResolvedValue({
      covered: 5,
      uncovered: 42,
      cameras_without_zones: 0,
    });

    const { container } = renderCard();
    await screen.findByText("42");

    const tinted = container.querySelector(".bg-warning\\/20");
    expect(tinted).not.toBeNull();
    expect(tinted?.className.split(/\s+/)).toContain("text-text");

    /*
     * ⚠ RANG YAGONA SIGNAL EMAS (WCAG 1.4.1): tint bilan BIRGA ikonka
     *   VA sabab jumlasi keladi. Ikonkaning mavjudligi `svg` bilan
     *   o'lchanadi — u `aria-hidden`, ya'ni roli bo'yicha topilmaydi.
     */
    expect(tinted?.querySelector("svg")).not.toBeNull();
  });
});

describe("yuklanish va xato", () => {
  test("yuklanayotganda `aria-busy` va skelet", () => {
    apiClientMock.apiFetch.mockReturnValue(new Promise(() => {}));

    const { container } = renderCard();

    expect(container.querySelector("[aria-busy='true']")).not.toBeNull();
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  test("⚠ xato XATO BLOKI EMAS, jim qator — `role='alert'` qo'yilmaydi", async () => {
    apiClientMock.apiFetch.mockRejectedValue(new Error("boom"));

    const { container } = renderCard();

    await waitFor(() =>
      expect(
        screen.getByText(messages.errors.loadFailedBody),
      ).toBeInTheDocument(),
    );
    expect(container.querySelector("[role='alert']")).toBeNull();
  });
});
