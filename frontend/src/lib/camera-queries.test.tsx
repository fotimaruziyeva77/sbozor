/**
 * Kamera so'rov qatlamining IKKI da'vosi: DOIRALASH va POLL CHEGARASI.
 *
 * NEGA AYNAN BU IKKISI:
 *
 *   1. DOIRALASH (CR-01 sinfi). Doiralanmagan kalit A bozorining
 *      kamerasini B bozorining sessiyasida ko'rsatardi va bu hech qanday
 *      xatoga sabab bo'lmasdi — ekran ochiladi, typecheck yashil. Faqat
 *      kalitning O'ZINI o'lchash uni ushlaydi.
 *
 *   2. POLL CHEGARASI. Cheksiz poll ham jimgina yashaydi: u ishlaydi,
 *      hech narsa yiqilmaydi, faqat ochiq qolgan tab serverni kunlab
 *      so'rab turadi (T-03-60). Chegaralar `refetchInterval` funksiyasi
 *      ichida yashaydi, ya'ni ularni faqat funksiyani CHAQIRIB o'lchash
 *      mumkin.
 *
 * ⚠ `refetchInterval` funksiyasi `QueryClient` orqali emas, TO'G'RIDAN-
 *   TO'G'RI chaqiriladi (soxta `query` obyekti bilan): haqiqiy poll
 *   testni 2 soniyalik oraliqlarga bog'lab qo'yardi va uch daqiqalik
 *   chegarani umuman o'lchab bo'lmasdi.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

const apiClientMock = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiClientMock.apiFetch };
});

import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";
import type { DiscoveryRunStatusValue } from "@/lib/api-types";
import {
  camerasKey,
  DISCOVERY_POLL_INTERVAL_MS,
  DISCOVERY_POLL_MAX_FAILURES,
  DISCOVERY_POLL_TIMEOUT_MS,
  discoveryPollInterval,
  discoveryRunKey,
  EMPTY_CAMERA_FILTERS,
  isDiscoveryTimedOut,
  LIVE_CONNECT_TIMEOUT_MS,
  LIVE_EXPIRY_WARNING_MS,
  LIVE_SESSION_MAX_MS,
  nvrDevicesKey,
  useCamerasQuery,
  useDiscoveryRunQuery,
} from "@/lib/camera-queries";

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const NVR_ID = "22222222-2222-4222-8222-222222222222";
const RUN_ID = "44444444-4444-4444-8444-444444444444";

let client: QueryClient;

function wrapper({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={client}>
      <AuthProvider>{children}</AuthProvider>
    </QueryClientProvider>
  );
}

function seedSession(marketId: string | null): void {
  setSession({
    accessToken: "test-access-token",
    principal: {
      userId: "33333333-3333-4333-8333-333333333333",
      phone: "+998900000000",
      fullName: "Test Admin",
      roles: ["market_admin"],
      marketId,
      marketName: "Karmana markaziy bozori",
      isPlatformAdmin: false,
      locale: "uz-Latn",
      mustChangePassword: false,
    },
    markets: [],
  });
}

beforeEach(() => {
  vi.resetAllMocks();
  clearSession();
  client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  apiClientMock.apiFetch.mockResolvedValue({ items: [], next_cursor: null });
});

afterEach(() => {
  client.clear();
  clearSession();
});

describe("kalitlar TUG'ILISHIDANOQ doiralangan (§S-10)", () => {
  test("har fabrika ['m', marketId, ...] shaklida boshlanadi", () => {
    expect(nvrDevicesKey(MARKET_ID)).toEqual(["m", MARKET_ID, "nvr-devices"]);
    expect(camerasKey(MARKET_ID, EMPTY_CAMERA_FILTERS)).toEqual([
      "m",
      MARKET_ID,
      "cameras",
      "list",
      EMPTY_CAMERA_FILTERS,
    ]);
    expect(discoveryRunKey(MARKET_ID, NVR_ID, RUN_ID)).toEqual([
      "m",
      MARKET_ID,
      "discovery-run",
      NVR_ID,
      RUN_ID,
    ]);
  });

  test("boshqa bozor kaliti BOSHQA — prefiks bo'yicha kesishmaydi", () => {
    const other = "99999999-9999-4999-8999-999999999999";

    expect(camerasKey(MARKET_ID, EMPTY_CAMERA_FILTERS)).not.toEqual(
      camerasKey(other, EMPTY_CAMERA_FILTERS),
    );
    // `["m", marketId]` prefiksi bitta bozorning BARCHA domen so'rovini
    // bildiradi — invalidatsiya aynan shu shaklga tayanadi.
    expect(camerasKey(MARKET_ID, EMPTY_CAMERA_FILTERS).slice(0, 2)).toEqual([
      "m",
      MARKET_ID,
    ]);
  });

  test("bozorsiz sessiyada so'rov YUBORILMAYDI (`enabled` kontrakti)", () => {
    seedSession(null);

    const { result } = renderHook(
      () => useCamerasQuery(EMPTY_CAMERA_FILTERS),
      { wrapper },
    );

    expect(result.current.fetchStatus).toBe("idle");
    expect(apiClientMock.apiFetch).not.toHaveBeenCalled();
  });

  test("bozor bor sessiyada so'rov ketadi (nazorat)", () => {
    seedSession(MARKET_ID);

    renderHook(() => useCamerasQuery(EMPTY_CAMERA_FILTERS), { wrapper });

    expect(apiClientMock.apiFetch).toHaveBeenCalledTimes(1);
    expect(apiClientMock.apiFetch).toHaveBeenCalledWith(
      expect.stringContaining("/cameras?"),
      expect.anything(),
    );
  });

  test("filtrlar so'rov yo'liga tushadi va kalitni ajratadi", () => {
    seedSession(MARKET_ID);

    renderHook(
      () =>
        useCamerasQuery({ nvrId: NVR_ID, status: "offline", archived: "true" }),
      { wrapper },
    );

    const path = apiClientMock.apiFetch.mock.calls[0][0] as string;
    expect(path).toContain(`nvr_id=${NVR_ID}`);
    expect(path).toContain("status=offline");
    expect(path).toContain("archived=true");
  });
});

/* -------------------------------------------------------------------------- */

/**
 * Poll qarori — SOF FUNKSIYA orqali o'lchanadi.
 *
 * ⚠ TanStack ning ichki `query.state` shakli O'QILMAYDI: u kutubxona
 *   versiyasi bilan o'zgaradigan xususiy yuza va unga tayangan test
 *   yangilanishda jimgina yashil bo'lib qolardi (yoki bo'sh obyektda
 *   "hech narsa qaytmadi" ni "to'xtadi" deb o'qirdi).
 */
function pollDecision(state: {
  status?: DiscoveryRunStatusValue;
  startedAt?: string;
  failures?: number;
}) {
  return discoveryPollInterval({
    status: state.status,
    startedAt: state.startedAt ?? new Date().toISOString(),
    failureCount: state.failures ?? 0,
    now: Date.now(),
  });
}

describe("poll kontrakti — CHEKSIZ POLL HECH QACHON (§5.3)", () => {
  test("faol holatda 2 soniyada bir so'raladi", () => {
    expect(pollDecision({ status: "queued" })).toBe(
      DISCOVERY_POLL_INTERVAL_MS,
    );
    expect(pollDecision({ status: "running" })).toBe(
      DISCOVERY_POLL_INTERVAL_MS,
    );
  });

  test("terminal holatda poll BUTUNLAY to'xtaydi", () => {
    expect(pollDecision({ status: "succeeded" })).toBe(false);
    expect(pollDecision({ status: "failed" })).toBe(false);
  });

  test("`started_at` dan 3 daqiqa o'tsa poll o'ladi (qotib qolgan worker)", () => {
    const old = new Date(Date.now() - DISCOVERY_POLL_TIMEOUT_MS - 1000);

    expect(
      pollDecision({ status: "running", startedAt: old.toISOString() }),
    ).toBe(false);
  });

  test("uch ketma-ket yiqilishdan keyin poll o'ladi (server javob bermayapti)", () => {
    // Bu IKKINCHI, mustaqil chegara: server umuman javob bermasa
    // `started_at` hech qachon kelmaydi va birinchi chegara mangu ochiq
    // qolardi.
    expect(
      pollDecision({ failures: DISCOVERY_POLL_MAX_FAILURES }),
    ).toBe(false);

    // Nazorat: ikkitasi hali chegara emas.
    expect(pollDecision({ failures: DISCOVERY_POLL_MAX_FAILURES - 1 })).toBe(
      DISCOVERY_POLL_INTERVAL_MS,
    );
  });

  test("yashirin tabda poll YO'Q", () => {
    seedSession(MARKET_ID);
    renderHook(() => useDiscoveryRunQuery(NVR_ID, RUN_ID), { wrapper });

    const cache = client
      .getQueryCache()
      .find({ queryKey: discoveryRunKey(MARKET_ID, NVR_ID, RUN_ID) });

    // Bu YAGONA joy TanStack ning saqlangan sozlamasini o'qiydi va u
    // ATAYIN: `refetchIntervalInBackground` — kutubxonaning O'Z xulqi,
    // ya'ni uni sof funksiyaga ko'chirib bo'lmaydi. Tip `unknown` orqali
    // ochiladi, chunki `QueryOptions` bu observer-darajasidagi maydonni
    // e'lon qilmaydi.
    const options = cache?.options as
      | { refetchIntervalInBackground?: boolean }
      | undefined;

    expect(options?.refetchIntervalInBackground).toBe(false);
  });

  test("`run_id` yo'q bo'lsa so'rov ham yo'q", () => {
    seedSession(MARKET_ID);

    const { result } = renderHook(
      () => useDiscoveryRunQuery(NVR_ID, null),
      { wrapper },
    );

    expect(result.current.fetchStatus).toBe("idle");
    expect(apiClientMock.apiFetch).not.toHaveBeenCalled();
  });
});

describe("isDiscoveryTimedOut — S5 chegarasi", () => {
  test("chegaradan oldin `false`, keyin `true`", () => {
    const start = "2026-08-03T10:00:00.000Z";
    const startMs = Date.parse(start);

    expect(isDiscoveryTimedOut(start, startMs + 1000)).toBe(false);
    expect(isDiscoveryTimedOut(start, startMs + DISCOVERY_POLL_TIMEOUT_MS)).toBe(
      true,
    );
  });

  test("buzuq sana chegarani ISHGA TUSHIRMAYDI", () => {
    // Panel S5 ga o'tmaydi — u YOLG'ON "javob bermayapti" xabari
    // bo'lardi. Poll'ning ikkinchi chegarasi (yiqilishlar) baribir bor.
    expect(isDiscoveryTimedOut("ertaga", Date.now())).toBe(false);
  });
});

describe("jonli sessiya konstantalari (§8.3)", () => {
  test("chegaralar UI-SPEC dagi o'lchangan qiymatlarga teng", () => {
    expect(LIVE_SESSION_MAX_MS).toBe(300_000);
    expect(LIVE_EXPIRY_WARNING_MS).toBe(30_000);
    expect(LIVE_CONNECT_TIMEOUT_MS).toBe(15_000);

    // Ogohlantirish sessiya ICHIDA bo'lishi shart, aks holda L4 holati
    // hech qachon ko'rinmasdi.
    expect(LIVE_EXPIRY_WARNING_MS).toBeLessThan(LIVE_SESSION_MAX_MS);
  });
});
