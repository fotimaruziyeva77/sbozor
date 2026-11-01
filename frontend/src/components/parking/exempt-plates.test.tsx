/**
 * Pul olinmaydigan mashinalar — ro'yxat serverdagi sozlamaning bir qismi,
 * shuning uchun har amal BUTUN hujjatni yangi versiya sifatida yuboradi.
 *
 * Da'volar: (1) raqam normallashtiriladi («85 c525 oa» → 85C525OA) va
 * hujjatning qolgan qismi (tarif) so'zma-so'z saqlanadi; (2) takror raqam
 * so'rovsiz rad etiladi; (3) direktor ro'yxatni ko'radi, lekin o'zgartira
 * olmaydi.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import {
  exemptPlatesOf,
  normalizePlate,
  withExemptPlates,
} from "@/components/parking/exempt-plates";
import { ExemptPlatesCard } from "@/components/parking/exempt-plates-card";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const apiClientMock = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiClientMock.apiFetch };
});

const { apiFetch } = apiClientMock;

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const SITE_ID = "parking-test0001";

const DOC = {
  tariff: { version: 1, rules: [{ category: "car", first_hour_soum: 4000 }] },
  update: { channel: "stable", auto: true },
  parking: {
    staff: [{ id: "kassir-1", label: "Kassir 1" }],
    exempt_plates: [{ plate: "01A001AA", label: "Direktor" }],
  },
  plugins: ["parking"],
};

function session(role: "market_admin" | "director"): void {
  setSession({
    accessToken: "test-access-token",
    principal: {
      fullName: "Test",
      isPlatformAdmin: false,
      locale: "uz-Latn",
      marketId: MARKET_ID,
      marketName: "Sinov bozori",
      mustChangePassword: false,
      phone: "+998900000000",
      roles: [role],
      userId: "33333333-3333-4333-8333-333333333333",
    },
    markets: [],
  });
}

/*
 * Soxta server SAQLANGANINI ESLAB QOLADI: saqlashdan keyin `edge-sites`
 * prefiksi bo'yicha barcha so'rovlar qayta o'qiladi va GET endi yangi
 * versiyani qaytarishi kerak — aks holda ro'yxat eskisiga qaytib qolardi.
 */
function mockConfig(): void {
  let current = { version: 3, doc: DOC as Record<string, unknown>, created_at: "2026-11-01T03:00:00Z" };
  apiFetch.mockImplementation((url: string, init?: { method?: string; body?: unknown }) => {
    if (!url.includes(`/edge-sites/${SITE_ID}/config`)) {
      return Promise.reject(new Error(`kutilmagan so'rov: ${url}`));
    }
    if (init?.method === "PUT") {
      const body = init.body as { doc: Record<string, unknown> };
      current = { version: current.version + 1, doc: body.doc, created_at: "2026-11-01T04:00:00Z" };
    }
    return Promise.resolve(current);
  });
}

function putCalls(): Array<{ doc: Record<string, unknown> }> {
  return apiFetch.mock.calls
    .filter((call) => (call[1] as { method?: string } | undefined)?.method === "PUT")
    .map((call) => (call[1] as { body: { doc: Record<string, unknown> } }).body);
}

function renderCard() {
  return render(
    <NextIntlClientProvider locale="uz-Latn" messages={messages} timeZone="Asia/Tashkent">
      <QueryClientProvider
        client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
      >
        <AuthProvider>
          <ExemptPlatesCard siteId={SITE_ID} />
        </AuthProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>,
  );
}

beforeEach(() => {
  vi.resetAllMocks();
  mockConfig();
});

afterEach(() => {
  clearSession();
});

describe("yordamchilar", () => {
  test("raqam normallashtiriladi: bo'shliq, kichik harf, chiziqcha yo'qoladi", () => {
    expect(normalizePlate(" 85 c525-oa ")).toBe("85C525OA");
  });

  test("ro'yxat bo'lmasa bo'sh; bo'sh yorliq tashlab ketiladi", () => {
    expect(exemptPlatesOf({ tariff: {} })).toEqual([]);
    expect(
      exemptPlatesOf({ parking: { exempt_plates: [{ plate: "01A001AA", label: " " }] } }),
    ).toEqual([{ plate: "01A001AA" }]);
  });

  test("withExemptPlates hujjatning qolgan qismiga tegmaydi", () => {
    const next = withExemptPlates(DOC, [{ plate: "85C525OA" }]);
    expect(next.tariff).toBe(DOC.tariff);
    expect(next.parking).toEqual({
      staff: DOC.parking.staff,
      exempt_plates: [{ plate: "85C525OA" }],
    });
  });
});

describe("bozor admini", () => {
  test("qo'shish — raqam normallashadi, PUT butun hujjat bilan ketadi", async () => {
    session("market_admin");
    renderCard();
    expect(await screen.findByText("01A001AA")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(messages.parkingReport.exempt.plateLabel), {
      target: { value: "85 c525 oa" },
    });
    fireEvent.change(screen.getByLabelText(messages.parkingReport.exempt.labelLabel), {
      target: { value: "Ishchi" },
    });
    fireEvent.click(screen.getByRole("button", { name: messages.parkingReport.exempt.add }));

    await waitFor(() => expect(putCalls()).toHaveLength(1));
    const sent = putCalls()[0].doc;
    expect(sent.tariff).toEqual(DOC.tariff);
    expect((sent.parking as { exempt_plates: unknown[] }).exempt_plates).toEqual([
      { plate: "01A001AA", label: "Direktor" },
      { plate: "85C525OA", label: "Ishchi" },
    ]);
    expect(await screen.findByText("85C525OA")).toBeInTheDocument();
  });

  test("takror raqam so'rovsiz rad etiladi", async () => {
    session("market_admin");
    renderCard();
    await screen.findByText("01A001AA");

    fireEvent.change(screen.getByLabelText(messages.parkingReport.exempt.plateLabel), {
      target: { value: "01a001aa" },
    });
    fireEvent.click(screen.getByRole("button", { name: messages.parkingReport.exempt.add }));

    expect(await screen.findByText(messages.parkingReport.exempt.errDuplicate)).toBeInTheDocument();
    expect(putCalls()).toHaveLength(0);
  });

  test("olib tashlash — tasdiqdan keyin ro'yxatsiz hujjat ketadi", async () => {
    session("market_admin");
    renderCard();
    await screen.findByText("01A001AA");

    fireEvent.click(
      screen.getByRole("button", {
        name: `${messages.parkingReport.exempt.remove}: 01A001AA`,
      }),
    );
    const dialog = await screen.findByRole("dialog");
    fireEvent.click(
      within(dialog).getByRole("button", { name: messages.parkingReport.exempt.remove }),
    );

    await waitFor(() => expect(putCalls()).toHaveLength(1));
    expect((putCalls()[0].doc.parking as { exempt_plates: unknown[] }).exempt_plates).toEqual([]);
  });
});

describe("direktor", () => {
  test("ro'yxatni ko'radi, lekin forma va tugmalar yo'q", async () => {
    session("director");
    renderCard();
    expect(await screen.findByText("01A001AA")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: messages.parkingReport.exempt.add })).toBeNull();
    expect(screen.queryByLabelText(messages.parkingReport.exempt.plateLabel)).toBeNull();
    expect(screen.getByText(messages.parkingReport.exempt.readOnly)).toBeInTheDocument();
  });
});
