/**
 * Kadr olish so'rov qatlamining IKKI da'vosi: DOIRALASH va POLL CHEGARASI.
 *
 * =============================================================================
 * ⚠ NEGA TIP TIZIMI YOLG'IZ YETARLI EMAS — O'LCHANGAN (04-02).
 *
 *   `02-20` global kalit konstantalarini ATAYIN o'chirgan, shunda
 *   doiralashni chetlab o'tish TypeScript XATOSI bo'lsin. Bu haqiqat,
 *   lekin YARIM haqiqat:
 *
 *     domainKey(marketId, "capture-runs", day)   ✅ to'g'ri
 *     domainKey("capture-runs", day)             ✅ TIP JIHATIDAN YAROQLI
 *
 *   Ikkinchi shakl ham kompilyatsiyadan o'tadi — `domainKey` ning
 *   birinchi parametri `string`, ya'ni domen nomi ham unga tushadi. Va
 *   natija jimgina falokat: kalit BARCHA bozorlar uchun bir xil bo'lib
 *   qoladi, ekran ochiladi, typecheck yashil, faqat A bozorining kun
 *   jurnali B bozorining sessiyasida ko'rinadi (CR-01 ning aynan o'zi).
 *
 *   Shuning uchun kalitning SHAKLI shu yerda, qiymat bo'yicha
 *   qulflanadi. Bu `camera-queries.test.tsx` da o'rnatilgan naqsh va u
 *   3-fazadan meros.
 * =============================================================================
 *
 * ⚠ `refetchInterval` funksiyasi `QueryClient` orqali emas, sof
 *   `capturePollInterval` chaqiruvi bilan o'lchanadi: haqiqiy poll
 *   testni 30 soniyalik oraliqqa bog'lab qo'yardi.
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

import type { CaptureRun } from "@/lib/api-types";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";
import {
  alertsKey,
  CAPTURE_POLL_INTERVAL_MS,
  capturePollInterval,
  captureDayKey,
  scheduleTodayKey,
  schedulesKey,
  snapshotKey,
  useCaptureDay,
  useScheduleToday,
} from "@/lib/snapshot-queries";

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const OTHER_MARKET_ID = "99999999-9999-4999-8999-999999999999";
const SNAPSHOT_ID = "55555555-5555-4555-8555-555555555555";
const TODAY = "2026-09-01";
const YESTERDAY = "2026-08-31";

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

function makeRun(status: string): CaptureRun {
  return {
    run_id: "66666666-6666-4666-8666-666666666666",
    camera_id: "77777777-7777-4777-8777-777777777777",
    channel_no: 3,
    camera_name: "Kiyim qatori",
    slot_time: "06:30:00",
    scheduled_at: "2026-09-01T01:30:00Z",
    status,
    attempts: 1,
    error_code: null,
    quality_verdict: null,
    snapshot_id: null,
  };
}

beforeEach(() => {
  vi.resetAllMocks();
  clearSession();
  client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  apiClientMock.apiFetch.mockResolvedValue({ items: [] });
});

afterEach(() => {
  client.clear();
  clearSession();
});

describe("kalitlar TUG'ILISHIDANOQ doiralangan (§5.4)", () => {
  test("har fabrika ['m', marketId, ...] shaklida boshlanadi", () => {
    expect(scheduleTodayKey(MARKET_ID)).toEqual([
      "m",
      MARKET_ID,
      "schedule",
      "today",
    ]);
    expect(schedulesKey(MARKET_ID)).toEqual(["m", MARKET_ID, "schedules"]);
    expect(captureDayKey(MARKET_ID, TODAY)).toEqual([
      "m",
      MARKET_ID,
      "capture-runs",
      TODAY,
    ]);
    expect(snapshotKey(MARKET_ID, SNAPSHOT_ID)).toEqual([
      "m",
      MARKET_ID,
      "snapshots",
      "detail",
      SNAPSHOT_ID,
    ]);
    expect(alertsKey(MARKET_ID, false)).toEqual([
      "m",
      MARKET_ID,
      "alerts",
      "false",
    ]);
  });

  test("boshqa bozor kaliti BOSHQA — prefiks bo'yicha kesishmaydi", () => {
    expect(captureDayKey(MARKET_ID, TODAY)).not.toEqual(
      captureDayKey(OTHER_MARKET_ID, TODAY),
    );
    expect(scheduleTodayKey(MARKET_ID)).not.toEqual(
      scheduleTodayKey(OTHER_MARKET_ID),
    );

    // `["m", marketId]` prefiksi bitta bozorning BARCHA domen so'rovini
    // bildiradi — invalidatsiya aynan shu shaklga tayanadi.
    for (const key of [
      scheduleTodayKey(MARKET_ID),
      schedulesKey(MARKET_ID),
      captureDayKey(MARKET_ID, TODAY),
      alertsKey(MARKET_ID, true),
    ]) {
      expect(key.slice(0, 2)).toEqual(["m", MARKET_ID]);
    }
  });

  test("ochiq va yopilgan ogohlantirishlar AYRIM kesh yozuvi", () => {
    // Bitta kalitda ushlash checkbox yoqilganda ESKI ro'yxatni
    // ko'rsatardi va admin «yopilgan alert yo'q ekan» degan xulosaga
    // kelardi.
    expect(alertsKey(MARKET_ID, true)).not.toEqual(alertsKey(MARKET_ID, false));
  });

  test("kun kalitning bir qismi — kun almashsa kesh yozuvi ham almashadi", () => {
    expect(captureDayKey(MARKET_ID, TODAY)).not.toEqual(
      captureDayKey(MARKET_ID, YESTERDAY),
    );
  });

  test("bozorsiz sessiyada so'rov YUBORILMAYDI (`enabled` kontrakti)", () => {
    seedSession(null);

    const { result } = renderHook(() => useScheduleToday(), { wrapper });

    expect(result.current.fetchStatus).toBe("idle");
    expect(apiClientMock.apiFetch).not.toHaveBeenCalled();
  });

  test("bozor bor sessiyada so'rov ketadi (nazorat)", () => {
    seedSession(MARKET_ID);

    renderHook(() => useScheduleToday(), { wrapper });

    expect(apiClientMock.apiFetch).toHaveBeenCalledTimes(1);
    expect(apiClientMock.apiFetch).toHaveBeenCalledWith(
      "/snapshot-schedules/today",
      expect.anything(),
    );
  });

  test("kun so'rov yo'liga tushadi", () => {
    seedSession(MARKET_ID);
    apiClientMock.apiFetch.mockResolvedValue({
      day: TODAY,
      summary: {
        planned: 0,
        done: 0,
        ok: 0,
        dark: 0,
        blank: 0,
        corrupt: 0,
        failed: 0,
        missed: 0,
      },
      rows: [],
      archived_present: false,
    });

    renderHook(() => useCaptureDay(TODAY, TODAY), { wrapper });

    expect(apiClientMock.apiFetch.mock.calls[0][0]).toBe(
      `/capture-runs?day=${TODAY}`,
    );
  });
});

/* -------------------------------------------------------------------------- */

describe("poll kontrakti — CHEKSIZ POLL HECH QACHON (§6.8)", () => {
  test("oraliq 30 soniya — 3-fazadagi 2 soniya BU YERGA ko'chirilmaydi", () => {
    expect(CAPTURE_POLL_INTERVAL_MS).toBe(30_000);
  });

  test("bugungi kunda faol qator bo'lsa poll ISHLAYDI", () => {
    for (const status of ["pending", "running"]) {
      expect(
        capturePollInterval({
          day: TODAY,
          todayIso: TODAY,
          rows: [makeRun(status)],
        }),
      ).toBe(CAPTURE_POLL_INTERVAL_MS);
    }
  });

  test("kun tugagach poll O'ZI to'xtaydi — terminal shart MA'LUMOTDAN", () => {
    // Qo'shimcha taymer yo'q va kerak ham emas: `succeeded`/`failed`/
    // `missed`/`skipped` — hammasi yakuniy.
    expect(
      capturePollInterval({
        day: TODAY,
        todayIso: TODAY,
        rows: [makeRun("succeeded"), makeRun("missed"), makeRun("failed")],
      }),
    ).toBe(false);

    // ⚠ `skipped` FAOL DEB HISOBLANMAYDI: u boshidanoq yakuniy (bozor
    //   kun o'rtasida ulangan). «Terminal emas» degan inkor shakli uni
    //   faol deb o'qib, kunni tugagandan keyin ham poll qilardi.
    expect(
      capturePollInterval({
        day: TODAY,
        todayIso: TODAY,
        rows: [makeRun("skipped")],
      }),
    ).toBe(false);
  });

  test("o'tgan kun HECH QACHON poll qilinmaydi — faol qator bo'lsa ham", () => {
    expect(
      capturePollInterval({
        day: YESTERDAY,
        todayIso: TODAY,
        rows: [makeRun("running")],
      }),
    ).toBe(false);
  });

  test("birinchi javob kelgunicha poll YOQILADI", () => {
    // `undefined` ni «faol qator yo'q» deb o'qish bugungi kunni birinchi
    // yuklashda muzlatib qo'yardi.
    expect(
      capturePollInterval({ day: TODAY, todayIso: TODAY, rows: undefined }),
    ).toBe(CAPTURE_POLL_INTERVAL_MS);

    // Bo'sh ro'yxat esa BOSHQA narsa: javob keldi va faol qator yo'q.
    expect(
      capturePollInterval({ day: TODAY, todayIso: TODAY, rows: [] }),
    ).toBe(false);
  });

  test("yashirin tabda poll YO'Q", () => {
    seedSession(MARKET_ID);
    apiClientMock.apiFetch.mockResolvedValue({
      day: TODAY,
      summary: {
        planned: 0,
        done: 0,
        ok: 0,
        dark: 0,
        blank: 0,
        corrupt: 0,
        failed: 0,
        missed: 0,
      },
      rows: [],
      archived_present: false,
    });

    renderHook(() => useCaptureDay(TODAY, TODAY), { wrapper });

    const entry = client
      .getQueryCache()
      .find({ queryKey: captureDayKey(MARKET_ID, TODAY) });

    /*
     * Bu YAGONA joy TanStack ning saqlangan sozlamasini o'qiydi va u
     * ATAYIN (`camera-queries.test.tsx:232-249` naqshi):
     * `refetchIntervalInBackground` — kutubxonaning O'Z xulqi, ya'ni
     * uni sof funksiyaga ko'chirib bo'lmaydi. Tip qo'lda ochiladi,
     * chunki `QueryOptions` bu observer-darajasidagi maydonni e'lon
     * qilmaydi.
     */
    const options = entry?.options as
      | { refetchIntervalInBackground?: boolean }
      | undefined;

    expect(entry).toBeDefined();
    expect(options?.refetchIntervalInBackground).toBe(false);
  });
});
