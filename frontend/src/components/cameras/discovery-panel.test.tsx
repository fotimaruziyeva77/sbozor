/**
 * KASHFIYOT PANELI — BOSQICHLAR VA POLL CHEGARASI (UI-SPEC §5.2, §5.3, §13.5).
 *
 * =============================================================================
 * IKKI GURUH, IKKI XIL DA'VO:
 *
 *   (a) BOSQICH MASHINASI (sof funksiya). S2a -> S2b o'tishi UI'ning
 *       backenddan TALAB qilgan narsasi (§5.2 [TALAB]): `channels_found`
 *       sub-oqim tekshiruvlaridan OLDIN yoziladi, aks holda admin ~50
 *       soniya davomida bir xil «yuklanmoqda» ni ko'radi. Bu yerda
 *       o'tish sof funksiya ustida qulflanadi — komponent ichida
 *       qoldirilgan qaror darvozadan jimgina o'tib ketardi (03-09
 *       sabotaji S3 ning aynan sinfi).
 *
 *   (b) POLL CHEGARASI (DOM). ⚠ «CHEKSIZ POLL HECH QACHON» — bu
 *       fazaning qat'iy qoidalaridan biri va uni FAQAT haqiqiy so'rov
 *       sanog'i bilan o'lchash mumkin: qotib qolgan yugurishda soat
 *       oldinga surilgandan keyin ham YANGI SO'ROV KETMASLIGI kerak.
 *
 * ⚠ SOXTA TAYMER: `vi.useFakeTimers()` — panel har soniyada `setInterval`
 *   bilan soatni yangilaydi va real vaqtda 180 soniya kutish mumkin
 *   emas. Soat `vi.setSystemTime()` bilan boshqariladi, chunki panel
 *   `Date.now()` ni O'QIYDI (u tashqi tizim).
 * =============================================================================
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import {
  DiscoveryPanel,
  discoveryStageOf,
  elapsedLabel,
} from "@/components/cameras/discovery-panel";
import type { DiscoveryRun } from "@/lib/api-types";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";
import {
  DISCOVERY_POLL_MAX_FAILURES,
  DISCOVERY_POLL_TIMEOUT_MS,
} from "@/lib/camera-queries";

const apiClientMock = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiClientMock.apiFetch };
});

const { apiFetch } = apiClientMock;

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const NVR_ID = "22222222-2222-4222-8222-222222222222";
const RUN_ID = "44444444-4444-4444-8444-444444444444";

const QUEUED_LABEL = messages.cameras.runQueued;
const DETECTING_LABEL = messages.cameras.runDetecting;
const TIMEOUT_LABEL = messages.cameras.runTimeout;
const LEAVE_HINT = messages.cameras.runLeaveHint;
const SLOW_HINT = messages.cameras.runSlowHint;
const DONE_LABEL = messages.cameras.runDone;
const CHECK_LABEL = messages.cameras.checkStatus;

/** Panelning soati boshlanadigan lahza — testlar shu nuqtadan hisoblaydi. */
const T0 = Date.parse("2026-08-03T09:30:00Z");

function makeRun(overrides: Partial<DiscoveryRun> = {}): DiscoveryRun {
  return {
    id: RUN_ID,
    nvr_id: NVR_ID,
    status: "running",
    started_at: new Date(T0).toISOString(),
    finished_at: null,
    channels_found: null,
    channels_added: null,
    channels_marked_offline: null,
    error_code: null,
    error_detail: null,
    ...overrides,
  };
}

/* ---------------------------------------------------------------------------
 * (a) BOSQICH MASHINASI — SOF FUNKSIYA
 * ------------------------------------------------------------------------ */

describe("discoveryStageOf — UI-SPEC §5.2 ning oltala holati", () => {
  const base = {
    channelsFound: null,
    failureCount: 0,
    mountedAt: T0,
    now: T0 + 1000,
    startedAt: new Date(T0).toISOString(),
  };

  test("S1 — `queued`", () => {
    expect(discoveryStageOf({ ...base, status: "queued" })).toBe("queued");
  });

  test("S1 — javob HALI KELMAGAN holat ham «navbatda» deb ko'rsatiladi", () => {
    expect(discoveryStageOf({ ...base, status: undefined })).toBe("queued");
  });

  test("S2a -> S2b — `channels_found` yozilishi bosqichni ALMASHTIRADI", () => {
    expect(
      discoveryStageOf({ ...base, channelsFound: null, status: "running" }),
    ).toBe("detecting");

    expect(
      discoveryStageOf({ ...base, channelsFound: 6, status: "running" }),
    ).toBe("probing");
  });

  test("`channels_found === 0` S2b ga O'TKAZMAYDI (ma'nosiz matn oldi olinadi)", () => {
    expect(
      discoveryStageOf({ ...base, channelsFound: 0, status: "running" }),
    ).toBe("detecting");
  });

  test("S3 va S4 — terminal holatlar", () => {
    expect(discoveryStageOf({ ...base, status: "succeeded" })).toBe("succeeded");
    expect(discoveryStageOf({ ...base, status: "failed" })).toBe("failed");
  });

  test("S5 — 180 soniyadan keyin timeout", () => {
    expect(
      discoveryStageOf({
        ...base,
        now: T0 + DISCOVERY_POLL_TIMEOUT_MS - 1,
        status: "running",
      }),
    ).toBe("detecting");

    expect(
      discoveryStageOf({
        ...base,
        now: T0 + DISCOVERY_POLL_TIMEOUT_MS,
        status: "running",
      }),
    ).toBe("timeout");
  });

  test("TERMINAL HOLAT TIMEOUTDAN USTUN — kelgan natija yashirilmaydi", () => {
    expect(
      discoveryStageOf({
        ...base,
        now: T0 + DISCOVERY_POLL_TIMEOUT_MS * 10,
        status: "succeeded",
      }),
    ).toBe("succeeded");
  });

  test("S5 — ketma-ket yiqilishlar MUSTAQIL chegara", () => {
    expect(
      discoveryStageOf({
        ...base,
        failureCount: DISCOVERY_POLL_MAX_FAILURES,
        status: "running",
      }),
    ).toBe("timeout");
  });

  test("`started_at` HALI YO'Q bo'lsa chegara MONTAJ lahzasidan hisoblanadi", () => {
    /*
     * ⚠ Usiz panel S1 da MANGU qotib qolardi: birinchi javob umuman
     *   kelmasa `started_at` hech qachon to'lmaydi va vaqt chegarasining
     *   boshlanish nuqtasi yo'q bo'lardi.
     */
    expect(
      discoveryStageOf({
        ...base,
        now: T0 + DISCOVERY_POLL_TIMEOUT_MS,
        startedAt: null,
        status: undefined,
      }),
    ).toBe("timeout");
  });
});

describe("elapsedLabel — o'tgan vaqt", () => {
  const seconds = (value: number) => `${value} soniya`;

  test("5 soniyagacha KO'RSATILMAYDI (miltillash oldi olinadi)", () => {
    expect(elapsedLabel(0, seconds)).toBeNull();
    expect(elapsedLabel(4_999, seconds)).toBeNull();
    expect(elapsedLabel(5_000, seconds)).toBe("5 soniya");
  });

  test("bir daqiqadan keyin `m:ss`", () => {
    expect(elapsedLabel(59_000, seconds)).toBe("59 soniya");
    expect(elapsedLabel(60_000, seconds)).toBe("1:00");
    expect(elapsedLabel(95_000, seconds)).toBe("1:35");
  });
});

/* ---------------------------------------------------------------------------
 * (b) DOM — poll va bosqich matni
 * ------------------------------------------------------------------------ */

function renderPanel(): ReturnType<typeof render> {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false }, queries: { retry: false } },
  });

  const tree: ReactElement = (
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      timeZone="Asia/Tashkent"
    >
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <DiscoveryPanel nvrId={NVR_ID} onClose={vi.fn()} runId={RUN_ID} />
        </AuthProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>
  );

  return render(tree);
}

function seedSession(): void {
  setSession({
    accessToken: "test-access-token",
    principal: {
      fullName: "Test Admin",
      isPlatformAdmin: false,
      locale: "uz-Latn",
      marketId: MARKET_ID,
      marketName: "Karmana markaziy bozori",
      mustChangePassword: false,
      phone: "+998900000000",
      roles: ["market_admin"],
      userId: "33333333-3333-4333-8333-333333333333",
    },
    markets: [],
  });
}

describe("DiscoveryPanel — DOM", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(T0);
    seedSession();
  });

  afterEach(() => {
    vi.useRealTimers();
    clearSession();
  });

  test("S2a: qurilma aniqlanmoqda + «sahifani yopsangiz ham davom etadi»", async () => {
    apiFetch.mockResolvedValue(makeRun());

    renderPanel();

    await waitFor(() => {
      expect(screen.getByText(DETECTING_LABEL)).toBeInTheDocument();
    });
    expect(screen.getByText(LEAVE_HINT)).toBeInTheDocument();
    // Bosqich matni — E'LON QILINADIGAN yagona narsa.
    expect(screen.getByRole("status")).toHaveTextContent(DETECTING_LABEL);
  });

  test("S2a -> S2b: `channels_found` kelganda matn almashadi", async () => {
    apiFetch.mockResolvedValueOnce(makeRun());
    apiFetch.mockResolvedValue(makeRun({ channels_found: 6 }));

    renderPanel();

    await waitFor(() => {
      expect(screen.getByText(DETECTING_LABEL)).toBeInTheDocument();
    });

    // Keyingi poll — 2 soniyadan keyin.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2_500);
    });

    await waitFor(() => {
      expect(
        screen.getByText(messages.cameras.runProbing.replace("{count}", "6")),
      ).toBeInTheDocument();
    });
  });

  test("o'tgan vaqt 5 soniyadan keyin chiqadi va E'LON QILINMAYDI", async () => {
    apiFetch.mockResolvedValue(makeRun());

    const { container } = renderPanel();

    await waitFor(() => {
      expect(screen.getByText(DETECTING_LABEL)).toBeInTheDocument();
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(6_000);
    });

    const hidden = container.querySelector('[aria-hidden="true"].tabular-nums');
    expect(hidden).not.toBeNull();
    expect(hidden?.textContent ?? "").toMatch(/soniya/u);
  });

  test("60 soniyadan keyin «sekin tarmoq» izohi qo'shiladi", async () => {
    apiFetch.mockResolvedValue(makeRun());

    renderPanel();

    await waitFor(() => {
      expect(screen.getByText(DETECTING_LABEL)).toBeInTheDocument();
    });
    expect(screen.queryByText(SLOW_HINT)).toBeNull();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(61_000);
    });

    await waitFor(() => {
      expect(screen.getByText(SLOW_HINT)).toBeInTheDocument();
    });
  });

  test("⚠ 180 soniyadan keyin POLL TO'XTAYDI va S5 ko'rinadi", async () => {
    // Qotib qolgan yugurish: server hamon `running` deydi.
    apiFetch.mockResolvedValue(
      makeRun({ started_at: new Date(T0 - DISCOVERY_POLL_TIMEOUT_MS).toISOString() }),
    );

    renderPanel();

    await waitFor(() => {
      expect(screen.getByText(TIMEOUT_LABEL)).toBeInTheDocument();
    });

    // ⚠ XATO RANGI ISHLATILMAYDI — S5 xato EMAS.
    expect(screen.getByRole("status")).toHaveTextContent(TIMEOUT_LABEL);
    expect(document.querySelector('[role="alert"]')).toBeNull();
    expect(
      screen.getByRole("button", { name: CHECK_LABEL }),
    ).toBeInTheDocument();

    // ⚠ ASOSIY ASSERT: soat oldinga surilganda YANGI SO'ROV KETMAYDI.
    const callsAtTimeout = apiFetch.mock.calls.length;
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000);
    });
    expect(apiFetch.mock.calls.length).toBe(callsAtTimeout);
  });

  test("terminal holatda poll to'xtaydi va natija paneli chiqadi", async () => {
    apiFetch.mockResolvedValue(
      makeRun({
        channels_added: 0,
        channels_found: 6,
        channels_marked_offline: 0,
        finished_at: new Date(T0 + 41_000).toISOString(),
        status: "succeeded",
      }),
    );

    renderPanel();

    await waitFor(() => {
      expect(screen.getByText(DONE_LABEL)).toBeInTheDocument();
    });

    const callsAfterTerminal = apiFetch.mock.calls.length;
    await act(async () => {
      await vi.advanceTimersByTimeAsync(20_000);
    });
    expect(apiFetch.mock.calls.length).toBe(callsAfterTerminal);

    // Natija paneli — anti-«buzuq ko'rinadi» jumlasi bilan.
    expect(screen.getByText(messages.cameras.runNoChanges)).toBeInTheDocument();
  });

  test("S4: `failed` da xato bloki chiqadi va FOKUS KO'CHMAYDI", async () => {
    apiFetch.mockResolvedValue(
      makeRun({
        error_code: "nvr_bad_credentials",
        finished_at: new Date(T0 + 3_000).toISOString(),
        status: "failed",
      }),
    );

    renderPanel();

    await waitFor(() => {
      expect(
        screen.getByText(messages.cameras.errorCause.nvr_bad_credentials),
      ).toBeInTheDocument();
    });

    // Xato bloki O'ZI e'lon qiladi; panel qo'shimcha `status` qo'ymaydi.
    expect(screen.getByRole("alert")).toBeInTheDocument();
    // ⚠ Fokus `body` da qoladi (§7.6 — job 60 soniyadan keyin qaytgan
    //   bo'lishi mumkin va foydalanuvchi boshqa ish qilayotgandir).
    expect(document.activeElement).toBe(document.body);
  });

  test("S1: `queued` holatida «Navbatga qo'yildi»", async () => {
    apiFetch.mockResolvedValue(makeRun({ status: "queued" }));

    renderPanel();

    await waitFor(() => {
      expect(screen.getByText(QUEUED_LABEL)).toBeInTheDocument();
    });
  });
});
