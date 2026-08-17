/**
 * TUSHUM TRENDI KARTASI — Y-2 DIREKTOR JONLANISHI (09-05 T2, 09-UI-SPEC §10.4).
 *
 * =============================================================================
 * ⛔ NIMA O'LCHANADI:
 *
 *   1. So'rov davri — KECHA bilan tugaydigan 7 kun (O-04): davr chegaralari
 *      MAVJUD biznes-kun yordamchilaridan (`businessDayIn`/`shiftIsoDay`),
 *      yangi util YO'Q.
 *   2. ⛔ «O'lchanmagan son chizilmaydi» (08 D-10): 7 kundan KAM nuqtada
 *      chiziq UMUMAN chizilmaydi — `EmptyState` + Hint.
 *   3. Sof SVG sparkline: `role="img"` + `<title>` + YONIDA matnli yig'indi —
 *      rang/shakl yolg'iz signal EMAS (§15). ⛔ Davr matni javobning
 *      `from_date`/`to_date` sidan — SO'RALGAN davrdan EMAS (server haqiqati).
 *   4. Real-vaqt [L-6]: birinchi yuklanishda «nafas» YO'Q; qiymat MAVJUD
 *      holatdan o'zgargandagina BIR martalik `.motion-breath`.
 *   5. Manba skani: komponentda `hasPermission(` 0 (G-motion-6(c) ning
 *      fayl-darajali sherigi) va 400/600 davomiylik tanlovi.
 *
 * ⚠ jsdom (09-RESEARCH Tuzoq 1): Tailwind CSS yuklanmaydi — tasdiqlar
 *   `className`/inline `style` SATRI ustida. SVG geometriya qiymatlari
 *   SATR sifatida beriladi (React son qiymatga `px` qo'shishi mumkin).
 * =============================================================================
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

const apiClientMock = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiClientMock.apiFetch };
});

import messages from "../../../messages/uz-Latn.json";
import { RevenueCard } from "@/components/dashboard/revenue-card";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const LOCALE = "uz-Latn";

/** `format.number()` bilan AYNI natija — next-intl ham `Intl` ni chaqiradi. */
const fmt = (value: number): string =>
  new Intl.NumberFormat(LOCALE).format(value);

/** `formatBusinessDay` bilan AYNI natija (12:00 UTC langar, medium). */
const fmtDay = (iso: string): string => {
  const [y, m, d] = iso.split("-").map(Number);
  return new Intl.DateTimeFormat(LOCALE, {
    dateStyle: "medium",
    timeZone: "Asia/Tashkent",
  }).format(new Date(Date.UTC(y, m - 1, d, 12)));
};

/** 7 qatorli javob — `from_date` ATAYIN so'ralganidan BOSHQA (server haqiqati). */
function revenuePayload(total: number) {
  const rows = [];
  for (let i = 0; i < 7; i += 1) {
    rows.push({
      business_date: `2026-08-${String(9 + i).padStart(2, "0")}`,
      charged_soum: 700_000 + i * 10_000,
      collected_soum: 600_000 + i * 15_000,
      diff_soum: -100_000 + i * 5_000,
    });
  }
  return {
    from_date: "2026-08-09",
    to_date: "2026-08-15",
    rows,
    total_collected_soum: total,
    total_charged_soum: 5_000_000,
    row_count: 7,
    shown_count: 7,
  };
}

function routeRevenue(payload: unknown): void {
  apiClientMock.apiFetch.mockImplementation((requested: string) => {
    if (requested.startsWith("/reports/revenue")) {
      return Promise.resolve(payload);
    }
    return Promise.reject(new Error(`kutilmagan so'rov: ${requested}`));
  });
}

function requestedPaths(): string[] {
  return apiClientMock.apiFetch.mock.calls.map((call) => String(call[0]));
}

let client: QueryClient;

function renderCard() {
  setSession({
    accessToken: "test-access-token",
    markets: [],
    principal: {
      userId: "33333333-3333-4333-8333-333333333333",
      phone: "+998900000000",
      fullName: "Test Direktor",
      roles: ["director"],
      marketId: MARKET_ID,
      marketName: "Karmana markaziy bozori",
      isPlatformAdmin: false,
      marketIsActive: true,
      locale: LOCALE,
      mustChangePassword: false,
    },
  });

  return render(
    <NextIntlClientProvider
      locale={LOCALE}
      messages={messages}
      timeZone="Asia/Tashkent"
    >
      <QueryClientProvider client={client}>
        <AuthProvider>
          <RevenueCard />
        </AuthProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>,
  );
}

beforeEach(() => {
  vi.resetAllMocks();
  client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
});

afterEach(() => {
  vi.useRealTimers();
  client.clear();
  clearSession();
});

describe("RevenueCard — so'rov davri", () => {
  test("⛔ KECHA bilan tugaydigan 7 kunlik davr so'raladi", async () => {
    /* Toshkentda 2026-08-17 (10:00) — kecha 08-16, boshi 08-10. */
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(new Date("2026-08-17T05:00:00Z"));

    routeRevenue(revenuePayload(4_550_000));
    renderCard();

    await waitFor(() => {
      expect(requestedPaths().length).toBeGreaterThan(0);
    });

    expect(
      requestedPaths().filter((p) =>
        p.startsWith("/reports/revenue"),
      ),
    ).toEqual(["/reports/revenue?from=2026-08-10&to=2026-08-16"]);
  });
});

describe("RevenueCard — o'lchanmagan son chizilmaydi (08 D-10)", () => {
  test("⛔ 7 kundan KAM nuqta — chiziq YO'Q, EmptyState + Hint", async () => {
    const short = revenuePayload(1_000_000);
    short.rows = short.rows.slice(0, 5);
    short.row_count = 5;
    short.shown_count = 5;
    routeRevenue(short);

    const { container } = renderCard();

    expect(
      await screen.findByText(messages.dashboard.revenueTrendEmpty),
    ).toBeInTheDocument();
    expect(
      screen.getByText(messages.dashboard.revenueTrendEmptyHint),
    ).toBeInTheDocument();

    /* Chiziq UMUMAN chizilmagan. */
    expect(container.querySelector("svg")).toBeNull();
  });
});

describe("RevenueCard — sof SVG sparkline", () => {
  test("role=img + <title> + matnli yig'indi; davr matni SERVER javobidan", async () => {
    routeRevenue(revenuePayload(4_550_000));
    const { container } = renderCard();

    /* Matnli yig'indi — `total_collected_soum` + birlik (rang yolg'iz emas). */
    await screen.findByText(fmt(4_550_000));
    expect(screen.getByText(messages.reports.amountUnit)).toBeInTheDocument();

    const svg = container.querySelector('svg[role="img"]');
    expect(svg).not.toBeNull();
    expect(svg?.querySelector("title")?.textContent).toBe(
      messages.dashboard.revenueTrendTitle,
    );

    /* Chiziq: `stroke-dashoffset` inline (jsdom sinf CSS'ini KO'RMAYDI). */
    const line = [...(svg?.querySelectorAll("path") ?? [])].find((el) =>
      (el.getAttribute("style") ?? "").includes("stroke-dashoffset"),
    );
    expect(line).not.toBeUndefined();
    expect(line?.getAttribute("style")).toContain("var(--ease-out)");

    /* Ostidagi maydon — TINT (0.08), to'yingan fon EMAS (§5.4). */
    const area = [...(svg?.querySelectorAll("path") ?? [])].find(
      (el) => el.getAttribute("fill-opacity") === "0.08",
    );
    expect(area).not.toBeUndefined();

    /*
     * ⛔ Davr matni — javobning `from_date`/`to_date` sidan. Mock ATAYIN
     *    so'ralgan davrdan boshqa sanani qaytaradi: ekranda AYNAN server
     *    sanasi turishi shart.
     */
    expect(container.textContent).toContain(fmtDay("2026-08-09"));
    expect(container.textContent).toContain(fmtDay("2026-08-15"));
  });

  test("kirish: `.motion-enter` + inline `--i` (60ms stagger)", async () => {
    routeRevenue(revenuePayload(4_550_000));
    const { container } = renderCard();

    await screen.findByText(fmt(4_550_000));

    const entering = container.querySelector(".motion-enter");
    expect(entering).not.toBeNull();
    const style = entering?.getAttribute("style") ?? "";
    expect(style).toContain("--i");
    /* ⛔ G-motion-3(b): inline uslubda `animation` YO'Q — faqat `--i`. */
    expect(style).not.toContain("animation");
  });
});

describe("RevenueCard — real-vaqt yangilanishi [L-6]", () => {
  test("⛔ birinchi yuklanishda nafas YO'Q; qiymat o'zgarganda BIR martalik", async () => {
    routeRevenue(revenuePayload(4_550_000));
    const { container } = renderCard();

    await screen.findByText(fmt(4_550_000));

    /* Birinchi yuklanish — nafas YO'Q. */
    expect(container.querySelector(".motion-breath")).toBeNull();

    /* Yangi to'lov: MAVJUD react-query invalidatsiyasi (poll EMAS). */
    routeRevenue(revenuePayload(4_600_000));
    await act(async () => {
      await client.invalidateQueries();
    });

    await waitFor(() => {
      expect(container.querySelector(".motion-breath")).not.toBeNull();
    });

    /* Yakuniy qiymat sr-only tugunda darhol to'liq. */
    await screen.findByText(fmt(4_600_000));

    /* Nafas BIR martalik: animatsiya tugashi bilan sinf olib tashlanadi. */
    const breathing = container.querySelector(".motion-breath") as HTMLElement;
    fireEvent.animationEnd(breathing);
    expect(container.querySelector(".motion-breath")).toBeNull();
  });
});

describe("RevenueCard — manba kontrakti", () => {
  test("⛔ `hasPermission(` 0 marta; count 400/600 davomiylik tanlovi bilan", () => {
    /* `import.meta.url` vite transformidan keyin ishonchsiz — cwd'dan. */
    const relative = path.join(
      "src",
      "components",
      "dashboard",
      "revenue-card.tsx",
    );
    let source: string | null = null;
    for (const base of [process.cwd(), path.join(process.cwd(), "frontend")]) {
      const candidate = path.resolve(base, relative);
      if (existsSync(candidate)) {
        source = readFileSync(candidate, "utf8");
        break;
      }
    }
    expect(source).not.toBeNull();

    /* ⛔ G-motion-6(c): huquq sharti SAHIFADA, komponentda EMAS. */
    expect(source).not.toContain("hasPermission(");
    /* [L-5]/[L-6]: birinchi ko'rinish 600ms, yangilanish 400ms. */
    expect(source).toMatch(/useCountUp\([^)]*\?\s*400\s*:\s*600\s*\)/u);
  });
});
