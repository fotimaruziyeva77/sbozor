/**
 * HISOBOT DOMENINING SO'ROV QATLAMI.
 *
 * =============================================================================
 * ⛔ 1. KALITLAR TUG'ILISHIDANOQ DOIRALANGAN — QIYMAT BO'YICHA.
 *
 *   Tip tizimi yolg'iz YETARLI EMAS va bu 04-02 da o'lchangan:
 *   `domainKey("occupancy", "day", …)` — ya'ni birinchi argument o'rniga
 *   domen nomini berish — TIP JIHATIDAN YAROQLI va kalitni HAMMA bozor
 *   uchun bir xil qilardi. Shuning uchun shakl qiymat bo'yicha qulflanadi.
 *
 * ⛔ 2. O'TGAN KUN UCHUN POLL YO'Q — LITERAL.
 *
 *   Yopilgan kun o'zgarmaydi. Poll qarori SOF FUNKSIYADA yashaydi
 *   (§S-13), chunki `useQuery` ichidagi shartni test qila olmaydigan
 *   holat 03-09 sabotaji S3 da o'lchangan.
 *
 * ⛔⛔ 3. ANIQLIK JAVOBI «ICHKI MOSLIK» MAYDONINI QABUL QILMAYDI.
 *
 *   D-16 bugungi sxemada IFODALAB BO'LMAYDI (05-11) va 05-12 uni
 *   javobdan NA SON, NA MAYDON sifatida chiqarib tashlagan. `z.object`
 *   bo'lsa, bunday maydon bir kun JIMGINA brauzerga yetib borardi va
 *   keyingi ijrochi «ma'lumot bor ekan» deb uni chizardi.
 *
 *   ⚠ DA'VO TOR: bu test SERVER shunday maydon YUBORMASLIGINI
 *     o'lchamaydi — uni 05-12 python tomonda o'lchagan. Bu yerdagi
 *     o'lchov — KLIENT uni QABUL QILMASLIGI, ya'ni ikkinchi qatlam.
 * =============================================================================
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

const apiClientMock = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiClientMock.apiFetch };
});

import {
  accuracyReportSchema,
  auditRoundSchema,
  occupancyDaySchema,
} from "@/lib/api-types";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";
import {
  OCCUPANCY_POLL_INTERVAL_MS,
  accuracyKey,
  occupancyDayKey,
  occupancyPollInterval,
  roundKey,
  useAccuracyReport,
  useAuditRound,
  useOccupancyDay,
} from "@/lib/occupancy-queries";

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const DAY = "2026-09-14";
const YESTERDAY = "2026-09-13";

let client: QueryClient;

function seedSession(roles: readonly string[]): void {
  setSession({
    accessToken: "test-access-token",
    principal: {
      userId: "33333333-3333-4333-8333-333333333333",
      phone: "+998900000000",
      fullName: "Test Director",
      roles: [...roles],
      marketId: MARKET_ID,
      marketName: "Karmana markaziy bozori",
      isPlatformAdmin: false,
      locale: "uz-Latn",
      mustChangePassword: false,
    },
    markets: [],
  });
}

function wrapper({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={client}>
      <AuthProvider>{children}</AuthProvider>
    </QueryClientProvider>
  );
}

/** Serverning HAQIQIY javob shakli (`OccupancyAccuracyResponse`). */
function accuracyPayload(overrides: Record<string, unknown> = {}) {
  return {
    from_date: "2026-08-16",
    to_date: "2026-09-14",
    drawn: 640,
    answered: 618,
    unanswered: 22,
    dont_know: 6,
    matrix: {
      true_occupied: 401,
      false_occupied: 23,
      false_empty: 38,
      true_empty: 150,
    },
    n: 612,
    measured: true,
    min_sample: 20,
    base_rate: 0.7173,
    correct: { point: 0.9003, lower: 0.874, upper: 0.9219 },
    false_occupied: { point: 0.0542, lower: 0.0364, upper: 0.0799 },
    false_empty: { point: 0.0866, lower: 0.0637, upper: 0.1166 },
    ...overrides,
  };
}

beforeEach(() => {
  vi.resetAllMocks();
  client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  seedSession(["director"]);
});

afterEach(() => {
  client.clear();
  clearSession();
});

/* -------------------------------------------------------------------------- */
/* 1. KESH KALITLARI                                                          */
/* -------------------------------------------------------------------------- */

describe("kesh kalitlari tug'ilishidanoq doiralangan", () => {
  test("uchala kalit ham bozor identifikatorini olib yuradi", () => {
    expect(occupancyDayKey("m1", DAY)).toEqual([
      "m",
      "m1",
      "occupancy",
      "day",
      DAY,
    ]);
    expect(roundKey("m1", DAY)).toEqual(["m", "m1", "occupancy", "round", DAY]);
    expect(accuracyKey("m1", null, null)).toEqual([
      "m",
      "m1",
      "occupancy",
      "accuracy",
      null,
      null,
    ]);
  });

  test("kun kalitning bir qismi — ikki kun bir yozuvda YASHAMAYDI", () => {
    expect(occupancyDayKey("m1", DAY)).not.toEqual(
      occupancyDayKey("m1", YESTERDAY),
    );
    expect(roundKey("m1", DAY)).not.toEqual(roundKey("m1", YESTERDAY));
  });

  test("davr aniqlik kalitining bir qismi (8-fazaga tayyorlik)", () => {
    expect(accuracyKey("m1", "2026-08-01", "2026-08-31")).not.toEqual(
      accuracyKey("m1", null, null),
    );
  });
});

/* -------------------------------------------------------------------------- */
/* 2. POLL QARORI                                                             */
/* -------------------------------------------------------------------------- */

describe("poll qarori", () => {
  test("⛔ o'tgan kun uchun `false`", () => {
    expect(occupancyPollInterval({ day: YESTERDAY, todayIso: DAY })).toBe(false);
  });

  test("bugungi kun uchun 60 soniya", () => {
    expect(occupancyPollInterval({ day: DAY, todayIso: DAY })).toBe(60_000);
    expect(OCCUPANCY_POLL_INTERVAL_MS).toBe(60_000);
  });

  test("⚠ 4-fazadagi 30 s dan IKKI BAROBAR sekin (qaror qayta hisoblangan)", () => {
    /*
     * Bu assert konstantani emas, QARORNI qulflaydi: kimdir «bir xil
     * bo'lsin» deb 30 000 ga tushirsa, u sabab bilan birga o'zgarishi
     * kerak (`occupancy-queries.ts` docstringi).
     */
    expect(OCCUPANCY_POLL_INTERVAL_MS).toBe(2 * 30_000);
  });
});

/* -------------------------------------------------------------------------- */
/* 3. SO'ROVLARNING XULQI                                                     */
/* -------------------------------------------------------------------------- */

describe("kunlik so'rov", () => {
  test("kalit va yo'l kutilgan shaklda", async () => {
    apiClientMock.apiFetch.mockResolvedValue({
      day: DAY,
      stalls: 1,
      occupied: 1,
      empty: 0,
      default_empty: 0,
      no_coverage: 0,
      human_confirmed: 0,
      items: [],
    });

    const { result } = renderHook(() => useOccupancyDay(DAY, DAY), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(apiClientMock.apiFetch).toHaveBeenCalledWith(
      `/occupancy?day=${DAY}`,
      expect.objectContaining({ schema: occupancyDaySchema }),
    );
  });

  test("bozorsiz sessiyada so'rov UMUMAN ketmaydi", async () => {
    clearSession();
    renderHook(() => useOccupancyDay(DAY, DAY), { wrapper });
    await waitFor(() => expect(apiClientMock.apiFetch).not.toHaveBeenCalled());
  });
});

describe("aniqlik so'rovi", () => {
  test("⛔ davr parametrlari YUBORILMAYDI — standart SERVERDA", async () => {
    apiClientMock.apiFetch.mockResolvedValue(accuracyReportSchema.parse(accuracyPayload()));

    const { result } = renderHook(() => useAccuracyReport(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(apiClientMock.apiFetch).toHaveBeenCalledWith(
      "/occupancy/accuracy",
      expect.objectContaining({ schema: accuracyReportSchema }),
    );
    const [path] = apiClientMock.apiFetch.mock.calls[0] as [string];
    expect(path).not.toContain("from");
    expect(path).not.toContain("to=");
  });
});

describe("tur holati so'rovi", () => {
  test("kun bo'yicha so'raladi", async () => {
    apiClientMock.apiFetch.mockResolvedValue({
      day: DAY,
      drawn: false,
      round_no: null,
      drawn_at: null,
      frame_size: null,
      sample_size: null,
      answered: null,
      unanswered: null,
      dont_know: null,
      fast_decisions: null,
    });

    const { result } = renderHook(() => useAuditRound(DAY, DAY), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(apiClientMock.apiFetch).toHaveBeenCalledWith(
      `/occupancy/round?day=${DAY}`,
      expect.objectContaining({ schema: auditRoundSchema }),
    );
  });
});

/* -------------------------------------------------------------------------- */
/* 4. ⛔⛔ O'LCHANMAGAN MIQDOR SXEMADAN O'TMAYDI                              */
/* -------------------------------------------------------------------------- */

describe("nazoratchining ichki mosligi javobga KIRA OLMAYDI (D-16)", () => {
  test("aniqlik javobi qat'iy — ortiqcha maydon RAD ETILADI", () => {
    expect(() =>
      accuracyReportSchema.parse({
        ...accuracyPayload(),
        self_consistency: 0.94,
      }),
    ).toThrow();
  });

  test("tur holati javobi ham qat'iy", () => {
    const round = {
      day: DAY,
      drawn: true,
      round_no: 3,
      drawn_at: "2026-09-14T01:10:00Z",
      frame_size: 420,
      sample_size: 30,
      answered: 26,
      unanswered: 4,
      dont_know: 2,
      fast_decisions: 1,
    };

    /*
     * ⚠ «Namuna holati» bloki — moslik qatorining ENG TABIIY uyi (§11.6
     *   uni aynan shu yerga qo'ygan). 05-12 shu sababdan IKKALA javobni
     *   ham skanerlagan; bu yerda ham ikkalasi alohida o'lchanadi.
     */
    expect(() => auditRoundSchema.parse(round)).not.toThrow();
    expect(() =>
      auditRoundSchema.parse({ ...round, self_consistency: 1 }),
    ).toThrow();
  });

  test("SALBIY NAZORAT — toza javob ikkala sxemadan ham O'TADI", () => {
    /*
     * ⚠ Usiz yuqoridagi ikki assert «sxema hamma narsani rad etadi»
     *   holatida ham yashil bo'lardi (§S-10).
     */
    expect(accuracyReportSchema.parse(accuracyPayload()).n).toBe(612);
    expect(accuracyReportSchema.parse(accuracyPayload()).min_sample).toBe(20);
  });
});
