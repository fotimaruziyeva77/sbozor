/**
 * JONLI KO'RISH — SESSIYA VA UNING CHEGARALARI (UI-SPEC §8, §13.5, T-03-69).
 *
 * =============================================================================
 * UCH GURUH, UCH XIL DA'VO:
 *
 *   (a) BOSQICH MASHINASI (sof funksiya). Sessiya chegarasi
 *       AVTORIZATSIYADAN QAT'I NAZAR ishlaydi — bu T-03-69 ning butun
 *       mazmuni: nazoratsiz qolgan jonli ko'rish RTSP oqimini cheksiz
 *       ushlab turib, NVR ning bitreyt byudjetini yeydi va bozor
 *       kuzatuvini yiqitadi.
 *
 *   (b) L0 — DIALOG OCHILISHI BILAN HECH NARSA BOSHLANMAYDI. Bu
 *       o'lchanadigan da'vo: token so'rovi YUBORILMAYDI va pleyer
 *       montaj qilinmaydi. Rejaning sabotaj bandi aynan shu chegarani
 *       tekshiradi.
 *
 *   (c) PLEYERNING HAYOT SIKLI. Yopilganda unmount, 5 daqiqada unmount,
 *       `[Davom ettirish]` da esa QAYTA MOUNT — «uzilmasdan yangilash»
 *       ataylab rad etilgan (§8.3) va uni faqat mount sanog'i bilan
 *       isbotlash mumkin.
 *
 * ⚠ PLEYER MOCK QILINADI. `video-rtc.js` WebSocket va `RTCPeerConnection`
 *   talab qiladi — jsdom ikkalasini ham bermaydi. Shuning uchun bu fayl
 *   pleyerning ICHINI emas, DIALOG bilan pleyer o'rtasidagi
 *   KONTRAKTNI o'lchaydi (mount / unmount / `url`). Pleyerning o'z
 *   xavfsizlik sozlamalari alohida, sof funksiya sifatida o'lchanadi
 *   (`applyPlayerPolicy` — quyida).
 * =============================================================================
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import {
  applyPlayerPolicy,
  isPlayerFailure,
  LIVE_PLAYER_SCRIPT_SRC,
  transportOf,
} from "@/components/cameras/live-player";
import {
  LiveViewDialog,
  liveStageOf,
  secondsLeft,
} from "@/components/cameras/live-view-dialog";
import type { Camera } from "@/lib/api-types";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";
import {
  LIVE_CONNECT_TIMEOUT_MS,
  LIVE_EXPIRY_WARNING_MS,
  LIVE_SESSION_MAX_MS,
} from "@/lib/camera-queries";

const apiClientMock = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiClientMock.apiFetch };
});

/**
 * Pleyer o'rniga kuzatiladigan qobiq.
 *
 * `data-mounts` — MODUL darajasidagi sanoq: qayta mount bo'lganda u
 * o'sadi, ya'ni «uzilmasdan yangilash» dan farqlanadi.
 */
const playerMock = vi.hoisted(() => ({ mounts: 0, lastUrl: "" }));

vi.mock("@/components/cameras/live-player", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("@/components/cameras/live-player")>();
  const { useEffect } = await import("react");
  return {
    ...actual,
    LivePlayer: ({
      onReady,
      url,
    }: {
      onReady: () => void;
      url: string;
    }) => {
      /*
       * `onReady` DIALOG tomonidan `useCallback` bilan barqarorlangan,
       * ya'ni bu effekt AYNAN montajda bir marta ishlaydi va mount
       * sanog'i haqiqiy qayta mountni o'lchaydi.
       */
      useEffect(() => {
        playerMock.mounts += 1;
        playerMock.lastUrl = url;
        onReady();
      }, [onReady, url]);
      return <div data-testid="live-player" data-url={url} />;
    },
  };
});

const { apiFetch } = apiClientMock;

const MARKET_ID = "11111111-1111-4111-8111-111111111111";

const VIEW_LABEL = messages.cameras.view;
const IDLE_LABEL = messages.cameras.liveIdle;
const RESUME_LABEL = messages.cameras.resume;
const EXPIRED_LABEL = messages.cameras.liveExpired;

const T0 = Date.parse("2026-08-03T09:30:00Z");

/** Token javobi — `url` OPAQUE va ekranga hech qachon chiqmaydi. */
const TICKET = {
  url: "/live/api/ws?src=opaque-handle&token=opaque-ticket",
  expires_in: 60,
  transport_hint: "webrtc",
};

function makeCamera(overrides: Partial<Camera> = {}): Camera {
  return {
    id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
    nvr_id: "22222222-2222-4222-8222-222222222222",
    channel_no: 7,
    name: "Sabzavot qatori",
    name_overridden: false,
    status: "online",
    is_archived: false,
    has_substream: true,
    source_ip: "192.168.1.101",
    source_model: "DS-2CD2143G0",
    last_seen_at: "2026-08-03T09:29:00Z",
    ...overrides,
  };
}

/* ---------------------------------------------------------------------------
 * (a) BOSQICH MASHINASI — SOF FUNKSIYA
 * ------------------------------------------------------------------------ */

describe("liveStageOf — UI-SPEC §8.2 ning yettita holati", () => {
  test("L0 / L1 / L6 — vaqtdan MUSTAQIL", () => {
    expect(liveStageOf({ elapsedMs: 0, phase: "idle" })).toBe("idle");
    expect(liveStageOf({ elapsedMs: 0, phase: "authorizing" })).toBe(
      "authorizing",
    );
    expect(liveStageOf({ elapsedMs: 0, phase: "error" })).toBe("error");
  });

  test("L2 -> L3", () => {
    expect(liveStageOf({ elapsedMs: 1_000, phase: "connecting" })).toBe(
      "connecting",
    );
    expect(liveStageOf({ elapsedMs: 1_000, phase: "playing" })).toBe("playing");
  });

  test("L6 — ulanish 15 soniyada o'rnatilmasa", () => {
    expect(
      liveStageOf({ elapsedMs: LIVE_CONNECT_TIMEOUT_MS - 1, phase: "connecting" }),
    ).toBe("connecting");
    expect(
      liveStageOf({ elapsedMs: LIVE_CONNECT_TIMEOUT_MS, phase: "connecting" }),
    ).toBe("error");
  });

  test("ULANGAN oqimga ulanish chegarasi QO'LLANMAYDI", () => {
    expect(
      liveStageOf({ elapsedMs: LIVE_CONNECT_TIMEOUT_MS + 1, phase: "playing" }),
    ).toBe("playing");
  });

  test("L4 — tugashdan 30 soniya oldin", () => {
    const warnAt = LIVE_SESSION_MAX_MS - LIVE_EXPIRY_WARNING_MS;
    expect(liveStageOf({ elapsedMs: warnAt - 1, phase: "playing" })).toBe(
      "playing",
    );
    expect(liveStageOf({ elapsedMs: warnAt, phase: "playing" })).toBe(
      "expiring",
    );
  });

  test("⚠ L5 — 5 daqiqalik chegara AVTORIZATSIYADAN QAT'I NAZAR (T-03-69)", () => {
    expect(liveStageOf({ elapsedMs: LIVE_SESSION_MAX_MS, phase: "playing" })).toBe(
      "expired",
    );
    // Hali ulanmagan sessiya ham chegaradan o'tolmaydi.
    expect(
      liveStageOf({ elapsedMs: LIVE_SESSION_MAX_MS, phase: "connecting" }),
    ).toBe("expired");
  });

  test("qolgan vaqt nolga tushadi va manfiy bo'lmaydi", () => {
    expect(secondsLeft(LIVE_SESSION_MAX_MS - 30_000)).toBe(30);
    expect(secondsLeft(LIVE_SESSION_MAX_MS)).toBe(0);
    expect(secondsLeft(LIVE_SESSION_MAX_MS + 10_000)).toBe(0);
  });
});

/* ---------------------------------------------------------------------------
 * PLEYERNING IKKI MAJBURIY SOZLAMASI (03-08 ko'rigi, UI-SPEC §14.2)
 * ------------------------------------------------------------------------ */

describe("applyPlayerPolicy — vendored pleyerning ikki majburiy sozlamasi", () => {
  test("⚠ TASHQI STUN XIZMATLARI O'CHIRILADI", () => {
    const target: Parameters<typeof applyPlayerPolicy>[0] = {
      pcConfig: {
        iceServers: [
          { urls: ["stun:stun.cloudflare.com:3478", "stun:stun.l.google.com:19302"] },
        ],
      },
    };

    applyPlayerPolicy(target);

    expect(target.pcConfig?.iceServers).toEqual([]);
    // Bozor tarmog'idan tashqariga chiqadigan bitta ham manzil qolmaydi.
    expect(JSON.stringify(target.pcConfig)).not.toContain("stun:");
  });

  test("⚠ AUDIO SO'RALMAYDI — oqim ovozsiz", () => {
    const target: Parameters<typeof applyPlayerPolicy>[0] = {
      media: "video,audio",
    };

    applyPlayerPolicy(target);

    expect(target.media).toBe("video");
    expect(target.media).not.toContain("audio");
    expect(target.media).not.toContain("microphone");
  });

  test("ko'rinmayotgan oqim ushlab turilmaydi (NVR bitreyt byudjeti)", () => {
    const target: Parameters<typeof applyPlayerPolicy>[0] = {
      background: true,
      visibilityCheck: false,
    };

    applyPlayerPolicy(target);

    expect(target.background).toBe(false);
    expect(target.visibilityCheck).toBe(true);
  });

  test("skript BIZNING originimizdan yuklanadi — go2rtc'dan emas (D-11)", () => {
    expect(LIVE_PLAYER_SCRIPT_SRC).toBe("/vendor/go2rtc/video-stream.js");
    expect(LIVE_PLAYER_SCRIPT_SRC.startsWith("/")).toBe(true);
    expect(LIVE_PLAYER_SCRIPT_SRC).not.toMatch(/^https?:/u);
  });

  test("transport qobiqning holat matnidan o'qiladi (§8.4)", () => {
    expect(transportOf("RTC")).toBe("WebRTC");
    expect(transportOf("MSE")).toBe("MSE");
    expect(transportOf("HLS")).toBe("HLS");
    // Oraliq holat transport EMAS.
    expect(transportOf("loading")).toBeNull();
    expect(isPlayerFailure("error")).toBe(true);
    expect(isPlayerFailure("MSE")).toBe(false);
  });
});

/* ---------------------------------------------------------------------------
 * (b) va (c) — DOM
 * ------------------------------------------------------------------------ */

function renderDialog(
  camera: Camera = makeCamera(),
): { onOpenChange: ReturnType<typeof vi.fn> } {
  const onOpenChange = vi.fn();
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
          <LiveViewDialog
            camera={camera}
            onOpenChange={onOpenChange}
            open
          />
        </AuthProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>
  );

  render(tree);
  return { onOpenChange };
}

function seedSession(): void {
  setSession({
    accessToken: "test-access-token",
    principal: {
      fullName: "Test Direktor",
      isPlatformAdmin: false,
      locale: "uz-Latn",
      marketId: MARKET_ID,
      marketName: "Karmana markaziy bozori",
      mustChangePassword: false,
      phone: "+998900000000",
      roles: ["director"],
      userId: "33333333-3333-4333-8333-333333333333",
    },
    markets: [],
  });
}

async function startViewing(): Promise<void> {
  fireEvent.click(screen.getByRole("button", { name: VIEW_LABEL }));
  await waitFor(() => {
    expect(screen.getByTestId("live-player")).toBeInTheDocument();
  });
}

describe("LiveViewDialog — DOM", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    playerMock.mounts = 0;
    playerMock.lastUrl = "";
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(T0);
    seedSession();
  });

  afterEach(() => {
    vi.useRealTimers();
    clearSession();
  });

  test("⚠ L0: dialog ochilishida OQIM BOSHLANMAYDI va TOKEN SO'RALMAYDI", () => {
    apiFetch.mockResolvedValue(TICKET);

    renderDialog();

    // Token so'rovi umuman yuborilmadi — NVR bitreyt byudjeti tegilmadi.
    expect(apiFetch).not.toHaveBeenCalled();
    // Pleyer DOM'da yo'q.
    expect(screen.queryByTestId("live-player")).toBeNull();
    // Ekranda esa aniq taklif turadi.
    expect(screen.getByText(IDLE_LABEL)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: VIEW_LABEL })).toBeInTheDocument();
  });

  test("[Ko'rish] bosilganda chipta olinadi va pleyer montaj qilinadi", async () => {
    apiFetch.mockResolvedValue(TICKET);

    renderDialog();
    await startViewing();

    expect(apiFetch).toHaveBeenCalledTimes(1);
    expect(String(apiFetch.mock.calls[0][0])).toContain("/live-token");
    expect(playerMock.mounts).toBe(1);
    expect(playerMock.lastUrl).toBe(TICKET.url);
  });

  test("⚠ 5 daqiqada pleyer UNMOUNT bo'ladi va L5 ko'rinadi", async () => {
    apiFetch.mockResolvedValue(TICKET);

    renderDialog();
    await startViewing();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(LIVE_SESSION_MAX_MS + 1_000);
    });

    await waitFor(() => {
      expect(screen.getByText(EXPIRED_LABEL)).toBeInTheDocument();
    });
    // Pleyer DOM'dan chiqdi -> oqim to'xtadi.
    expect(screen.queryByTestId("live-player")).toBeNull();
    // ⚠ XATO RANGI ISHLATILMAYDI — normal tugash.
    expect(document.querySelector('[role="alert"]')).toBeNull();
  });

  test("L4: tugashdan oldin ogohlantiriladi, LEKIN video davom etadi", async () => {
    apiFetch.mockResolvedValue(TICKET);

    renderDialog();
    await startViewing();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(
        LIVE_SESSION_MAX_MS - LIVE_EXPIRY_WARNING_MS + 1_000,
      );
    });

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: RESUME_LABEL }),
      ).toBeInTheDocument();
    });
    // Pleyer HAMON DOM'da — ogohlantirish videoni to'smaydi.
    expect(screen.getByTestId("live-player")).toBeInTheDocument();
  });

  test("⚠ [Davom ettirish] pleyerni QAYTA MOUNT qiladi (uzilmasdan yangilash YO'Q)", async () => {
    apiFetch.mockResolvedValue(TICKET);

    renderDialog();
    await startViewing();
    expect(playerMock.mounts).toBe(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(LIVE_SESSION_MAX_MS + 1_000);
    });
    await waitFor(() => {
      expect(screen.getByText(EXPIRED_LABEL)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: RESUME_LABEL }));

    await waitFor(() => {
      expect(screen.getByTestId("live-player")).toBeInTheDocument();
    });

    // YANGI chipta olindi va pleyer YANGIDAN montaj qilindi.
    expect(apiFetch).toHaveBeenCalledTimes(2);
    expect(playerMock.mounts).toBe(2);
  });

  test("dialog yopilganda pleyer DARHOL unmount bo'ladi", async () => {
    apiFetch.mockResolvedValue(TICKET);

    const { rerender } = renderDialogWithRerender();
    fireEvent.click(screen.getByRole("button", { name: VIEW_LABEL }));
    await waitFor(() => {
      expect(screen.getByTestId("live-player")).toBeInTheDocument();
    });

    rerender(false);

    expect(screen.queryByTestId("live-player")).toBeNull();
  });

  test("⚠ oqim identifikatori DOM'da HECH QAYERDA ko'rinmaydi (§8.7)", async () => {
    apiFetch.mockResolvedValue(TICKET);

    renderDialog();
    await startViewing();

    // Opaque manzil faqat pleyerga uzatiladi; ko'rinadigan matnda yo'q.
    expect(document.body.textContent).not.toContain("opaque-handle");
    expect(document.body.textContent).not.toContain(TICKET.url);
    // Ulashish affordansi ham yo'q.
    expect(screen.queryByRole("link")).toBeNull();
  });

  test("404: kamera topilmadi va ro'yxatni yangilash taklif qilinadi", async () => {
    const { ApiError } = await import("@/lib/api-client");
    apiFetch.mockRejectedValue(new ApiError(404, "camera_not_found", {}));

    renderDialog();
    fireEvent.click(screen.getByRole("button", { name: VIEW_LABEL }));

    await waitFor(() => {
      expect(screen.getByText(messages.cameras.liveNotFound)).toBeInTheDocument();
    });
    expect(screen.queryByTestId("live-player")).toBeNull();
  });
});

/** Yopilishni o'lchash uchun `open` ni boshqaradigan variant. */
function renderDialogWithRerender(): { rerender: (open: boolean) => void } {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false }, queries: { retry: false } },
  });
  const camera = makeCamera();

  const tree = (open: boolean): ReactElement => (
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      timeZone="Asia/Tashkent"
    >
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <LiveViewDialog
            camera={camera}
            onOpenChange={vi.fn()}
            open={open}
          />
        </AuthProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>
  );

  const view = render(tree(true));
  return { rerender: (open: boolean) => view.rerender(tree(open)) };
}
