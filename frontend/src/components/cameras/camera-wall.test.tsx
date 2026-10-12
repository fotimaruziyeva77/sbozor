/**
 * Kameralar devori — bozor kompyuteri O'CHIQ bo'lganda (261011).
 *
 * =============================================================================
 * ⛔⛔ PROD'DA O'LCHANGAN: kompyuter 11:32 da o'chgan, kechqurun devor
 *     ochilganda 16 katakning har biri jim yiqilib «jonli emas» belgisiga
 *     tushgan — umumiy sabab hech qayerda aytilmagan, har katak esa alohida
 *     so'rov (va alohida audit yozuvi) yuborgan.
 *
 *     Ikki da'vo: devor ustida BITTA xabar chiqadi va kompyuter o'chiq
 *     ekani ma'lum bo'lgach QOLGAN kataklar so'rov yubormaydi.
 * =============================================================================
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import { CameraWall } from "@/components/cameras/camera-wall";
import type { Camera } from "@/lib/api-types";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const apiClientMock = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiClientMock.apiFetch };
});

import { ApiError } from "@/lib/api-client";

const { apiFetch } = apiClientMock;

const MARKET_ID = "11111111-1111-4111-8111-111111111111";

function kamera(id: string, name: string): Camera {
  return {
    id,
    nvr_id: "22222222-2222-4222-8222-222222222222",
    channel_no: 1,
    name,
    name_overridden: false,
    status: "online",
    is_archived: false,
    has_substream: true,
    source_ip: "192.168.1.101",
    source_model: "DS-2CD1043G2-I",
    last_seen_at: "2026-10-11T06:30:00Z",
    last_snapshot_id: null,
    last_capture_at: null,
  } as Camera;
}

const KAMERALAR = [
  kamera("cccccccc-cccc-4ccc-8ccc-000000000001", "KB 1-4"),
  kamera("cccccccc-cccc-4ccc-8ccc-000000000002", "KB 5-8"),
];

function chiptaSorovlari(): string[] {
  return apiFetch.mock.calls
    .map((call) => String(call[0]))
    .filter((url) => url.includes("/live-token"));
}

beforeEach(() => {
  vi.resetAllMocks();
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
});

afterEach(() => {
  clearSession();
});

describe("kameralar devori — bozor kompyuteri o'chiq (261011)", () => {
  test("⛔ devor ustida BITTA xabar va qolgan kataklar so'rov YUBORMAYDI", async () => {
    apiFetch.mockImplementation((url: string) => {
      if (url.includes("/live-token")) {
        return Promise.reject(
          new ApiError(503, "live_agent_offline", {
            detail: "live_agent_offline",
            agent_last_seen_at: "2026-10-11T06:32:00+00:00",
          }),
        );
      }
      if (url.startsWith("/cameras")) {
        return Promise.resolve({ items: KAMERALAR, next_cursor: null, newest_capture_at: null });
      }
      return Promise.resolve({ items: [] });
    });

    render(
      <NextIntlClientProvider locale="uz-Latn" messages={messages} timeZone="Asia/Tashkent">
        <QueryClientProvider
          client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
        >
          <AuthProvider>
            <CameraWall />
          </AuthProvider>
        </QueryClientProvider>
      </NextIntlClientProvider>,
    );

    const xabar = await screen.findByText((matn) =>
      matn.startsWith(messages.cameras.wallAgentOfflineAt.split("{time}")[0]),
    );
    expect(xabar.closest('[role="status"]')).not.toBeNull();

    // Ikkinchi katak o'z navbatini (siljish bilan) KUTIB OLADI va baribir
    // so'rov yubormaydi — kompyuter o'chiq ekani allaqachon ma'lum.
    await new Promise((resolve) => setTimeout(resolve, 700));
    await waitFor(() => {
      expect(chiptaSorovlari()).toHaveLength(1);
    });
  });
});
