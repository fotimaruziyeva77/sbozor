/**
 * BANDLIK HALQASI — Y-2 DIREKTOR JONLANISHI (09-05 T2, 09-UI-SPEC §10.4).
 *
 * =============================================================================
 * ⛔ NIMA O'LCHANADI:
 *
 *   1. ⛔⛔ KECHAgi kun so'raladi (09-RESEARCH Tuzoq 3/4): bugungi javob
 *      odatda BO'SH (materializatsiya ertasi 03:40, `DAY_CLOSE_CRON`) va
 *      `day === todayIso` bo'lganda `occupancyPollInterval` avtomatik
 *      poll'ni YOQARDI — §10.6 «poll QO'SHILMAYDI» qoidasi jimgina
 *      buzilardi. Kecha so'ralganda poll O'ZI o'chadi — bu 61s dan keyin
 *      so'rov soni bilan O'LCHANADI.
 *   2. ⛔ `stalls === 0` — «kun HALI YOPILMAGAN», «hamma rasta bo'sh» EMAS:
 *      halqa CHIZILMAYDI (nol bilan halqa — TAQIQ, T-05-04).
 *   3. Sof SVG donut: `role="img"` + `<title>` + YONIDA matnli yig'indi
 *      (`dashboard.occupancySummary`) — rang yolg'iz signal EMAS. Sarlavha
 *      ostida qaysi KUN — `formatBusinessDay` (yagona sana yo'li).
 *   4. Manba skani: `hasPermission(` 0 (G-motion-6(c) fayl-darajali sherigi).
 *
 * ⚠ jsdom (09-RESEARCH Tuzoq 1): tasdiqlar inline `style`/atribut ustida;
 *   SVG qiymatlari SATR (React son qiymatga `px` qo'shishi mumkin).
 * =============================================================================
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor } from "@testing-library/react";
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
import { OccupancyDonut } from "@/components/dashboard/occupancy-donut";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const LOCALE = "uz-Latn";

/** `formatBusinessDay` bilan AYNI natija (12:00 UTC langar, medium). */
const fmtDay = (iso: string): string => {
  const [y, m, d] = iso.split("-").map(Number);
  return new Intl.DateTimeFormat(LOCALE, {
    dateStyle: "medium",
    timeZone: "Asia/Tashkent",
  }).format(new Date(Date.UTC(y, m - 1, d, 12)));
};

/** Yopilgan kun javobi — `items` bo'sh: donut faqat hisoblagichlarni o'qiydi. */
const OCCUPANCY_DAY = {
  day: "2026-08-16",
  stalls: 100,
  occupied: 68,
  empty: 24,
  default_empty: 5,
  no_coverage: 3,
  human_confirmed: 12,
  items: [],
};

function routeOccupancy(payload: unknown): void {
  apiClientMock.apiFetch.mockImplementation((requested: string) => {
    if (requested.startsWith("/occupancy")) return Promise.resolve(payload);
    return Promise.reject(new Error(`kutilmagan so'rov: ${requested}`));
  });
}

function requestedPaths(): string[] {
  return apiClientMock.apiFetch.mock.calls.map((call) => String(call[0]));
}

let client: QueryClient;

function renderDonut() {
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
          <OccupancyDonut />
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

describe("OccupancyDonut — KECHA va poll", () => {
  test("⛔ KECHAgi kun so'raladi va 61s dan keyin ham poll YO'Q", async () => {
    /* Toshkentda 2026-08-17 (10:00) — kecha 08-16. */
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(new Date("2026-08-17T05:00:00Z"));

    routeOccupancy(OCCUPANCY_DAY);
    renderDonut();

    await waitFor(() => {
      expect(requestedPaths().length).toBeGreaterThan(0);
    });

    const occupancyRequests = () =>
      requestedPaths().filter((p) => p.startsWith("/occupancy"));

    /* ⛔ Aynan KECHA: bugungi kun so'ralsa javob BO'SH bo'lardi (Tuzoq 3). */
    expect(occupancyRequests()).toEqual(["/occupancy?day=2026-08-16"]);

    /*
     * ⛔ §10.6: avtomatik poll YO'Q. `occupancyPollInterval` kecha uchun
     *    `false` qaytaradi — 61s (poll oralig'i 60s) o'tsa ham so'rov
     *    soni O'SMAYDI.
     */
    await act(async () => {
      await vi.advanceTimersByTimeAsync(61_000);
    });
    expect(occupancyRequests()).toEqual(["/occupancy?day=2026-08-16"]);
  });
});

describe("OccupancyDonut — o'lchanmagan son chizilmaydi (T-05-04)", () => {
  test("⛔ `stalls === 0` (kun hali yopilmagan) — halqa YO'Q, `occupancyEmpty`", async () => {
    routeOccupancy({
      ...OCCUPANCY_DAY,
      stalls: 0,
      occupied: 0,
      empty: 0,
      default_empty: 0,
      no_coverage: 0,
      human_confirmed: 0,
    });
    const { container } = renderDonut();

    expect(
      await screen.findByText(messages.dashboard.occupancyEmpty),
    ).toBeInTheDocument();

    /* ⛔ Nol bilan halqa chizish TAQIQ — SVG umuman yo'q. */
    expect(container.querySelector("svg")).toBeNull();
  });
});

describe("OccupancyDonut — sof SVG halqa", () => {
  test("role=img + <title> + matnli yig'indi + formatBusinessDay kuni", async () => {
    routeOccupancy(OCCUPANCY_DAY);
    const { container } = renderDonut();

    /* Matnli yig'indi — rang yolg'iz signal emas (§15). */
    expect(
      await screen.findByText("68 band · 24 bo'sh"),
    ).toBeInTheDocument();

    const svg = container.querySelector('svg[role="img"]');
    expect(svg).not.toBeNull();
    expect(svg?.querySelector("title")?.textContent).toBe(
      messages.dashboard.occupancyTitle,
    );

    /* Sarlavha ostida qaysi KUN — javobning `day` maydonidan. */
    expect(container.textContent).toContain(fmtDay("2026-08-16"));

    /* Halqa: dasharray 226, rotate(-90), offset inline. */
    const circles = [...(svg?.querySelectorAll("circle") ?? [])];
    expect(circles.length).toBe(2);

    const arc = circles.find((el) =>
      (el.getAttribute("style") ?? "").includes("stroke-dashoffset"),
    );
    expect(arc).not.toBeUndefined();
    expect(arc?.getAttribute("style")).toContain("var(--ease-out)");
    expect(arc?.getAttribute("transform")).toContain("rotate(-90");

    /*
     * Chizilish nishoni — `226 -> hisoblangan`: 100 rastadan 68 band ->
     * offset = round(226 * (1 - 0.68)) = 72. Chizish geometriyasi —
     * vizualizatsiya, ekranga FOIZ chiqarilmaydi.
     */
    await waitFor(() => {
      expect((arc as SVGCircleElement).getAttribute("style")).toContain(
        "stroke-dashoffset: 72",
      );
    });
  });

  test("kirish: `.motion-enter` + inline `--i` (60ms stagger)", async () => {
    routeOccupancy(OCCUPANCY_DAY);
    const { container } = renderDonut();

    await screen.findByText("68 band · 24 bo'sh");

    const entering = container.querySelector(".motion-enter");
    expect(entering).not.toBeNull();
    const style = entering?.getAttribute("style") ?? "";
    expect(style).toContain("--i");
    /* ⛔ G-motion-3(b): inline uslubda `animation` YO'Q — faqat `--i`. */
    expect(style).not.toContain("animation");
  });
});

describe("OccupancyDonut — manba kontrakti", () => {
  test("⛔ `hasPermission(` 0 marta — huquq sharti SAHIFADA", () => {
    const relative = path.join(
      "src",
      "components",
      "dashboard",
      "occupancy-donut.tsx",
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

    /* ⛔ G-motion-6(c): komponent o'zini o'zi himoya qilmaydi. */
    expect(source).not.toContain("hasPermission(");
    /* ⛔ KECHA — `shiftIsoDay(todayIso, -1)` (Tuzoq 3/4 yechimi). */
    expect(source).toContain("shiftIsoDay");
  });
});
