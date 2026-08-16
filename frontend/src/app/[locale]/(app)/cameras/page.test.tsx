/**
 * KAMERALAR SAHIFASI — HUQUQ KO'ZGUSINING **WIRING** O'LCHOVI (Topilma №J).
 *
 * =============================================================================
 * ⛔ BU FAYL KOMPONENTNI EMAS, ULANISHNI O'LCHAYDI.
 *
 *   `nvr-card.test.tsx` `canManage` PROPI bo'yicha o'lchaydi — ya'ni u
 *   komponent qoidaga bo'ysunishini isbotlaydi. Topilma №J esa aynan
 *   SHU YERDA tug'ilgan edi: qoida bor edi, prop uzatilmagan edi. Sahifa
 *   `canManage` ni allaqachon hisoblaydi (`page.tsx:128`) va uni
 *   to'rtta iste'molchidan UCHTASIGA uzatgan; `NvrCard` esa tushib
 *   qolgan. Prop bo'yicha o'lchov bunday nosozlikni HECH QACHON
 *   ko'rmasdi.
 *
 *   Shuning uchun bu yerda mock qilinadigan narsa AYNAN BITTA — tarmoq
 *   (`apiFetch`). Rol HAQIQIY (`setSession` -> `principal.roles`) va
 *   `hasPermission` HAQIQIY, ya'ni `rbac.ts` matritsasi ham o'lchov
 *   zanjirining ichida.
 *
 * ⛔ MOCK YO'L BO'YICHA MARSHRUTLANADI va NOMA'LUM YO'L RAD ETILADI:
 *    `undefined` qaytaruvchi mock sxema validatsiyasida tushunarsiz xato
 *    berib, yo'l xatosini yashirardi.
 *
 * ⚠ `inspector` shoxi IKKI TOMONLAMA o'lchanadi: matn ko'rinadi VA
 *   `apiFetch` UMUMAN chaqirilmaydi. Faqat matnni tekshirish «huquq
 *   tekshiruvi so'rovdan OLDIN» kontraktini (`page.tsx:53-58`)
 *   o'lchamasdi.
 * =============================================================================
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { NuqsTestingAdapter } from "nuqs/adapters/testing";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

const apiClientMock = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiClientMock.apiFetch };
});

vi.mock("sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}));

import messages from "../../../../../messages/uz-Latn.json";
import CamerasPage from "./page";
import type { NvrDevice } from "@/lib/api-types";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const TIME_ZONE = "Asia/Tashkent";
const NOW = new Date("2026-08-16T09:00:00Z");

const RESCAN_LABEL = messages.cameras.rescan;
const PASSWORD_LABEL = messages.cameras.updatePassword;
const DIAGNOSTICS_LABEL = messages.cameras.diagnostics;
const MANAGE_LABELS = [RESCAN_LABEL, PASSWORD_LABEL, DIAGNOSTICS_LABEL];

const DEVICE: NvrDevice = {
  id: "22222222-2222-4222-8222-222222222222",
  host: "192.168.1.64",
  port: 80,
  use_tls: false,
  username: "admin",
  model: "DS-7732NI-M4",
  serial_number: "DS7732NIM420250114",
  firmware_version: "V4.30.085",
  device_type: "NVR",
  rtsp_port: 554,
  rtsp_port_assumed: false,
  tunnel_subnet: "192.168.1.0/24",
  last_discovery_at: "2026-08-16T05:30:00Z",
  has_password: true,
};

const COVERAGE = { covered: 12, uncovered: 3, cameras_without_zones: 1 };

function routeFetch(): void {
  apiClientMock.apiFetch.mockImplementation((path: string) => {
    if (path.startsWith("/nvr-devices")) {
      return Promise.resolve({ items: [DEVICE] });
    }
    if (path.startsWith("/cameras?")) {
      return Promise.resolve({ items: [], next_cursor: null });
    }
    if (path.startsWith("/camera-zones/coverage")) {
      return Promise.resolve(COVERAGE);
    }
    return Promise.reject(new Error(`kutilmagan so'rov: ${path}`));
  });
}

/** AYNI marshrutlash, LEKIN bozorda hali NVR yo'q (E-1 holati). */
function routeFetchWithoutDevice(): void {
  apiClientMock.apiFetch.mockImplementation((path: string) => {
    if (path.startsWith("/nvr-devices")) {
      return Promise.resolve({ items: [] });
    }
    if (path.startsWith("/cameras?")) {
      return Promise.resolve({ items: [], next_cursor: null });
    }
    if (path.startsWith("/camera-zones/coverage")) {
      return Promise.resolve(COVERAGE);
    }
    return Promise.reject(new Error(`kutilmagan so'rov: ${path}`));
  });
}

/** DOM'ga tushgan `apiFetch` yo'llari — birinchi argument satri. */
function requestedPaths(): string[] {
  return apiClientMock.apiFetch.mock.calls.map((call) => String(call[0]));
}

let client: QueryClient;

function renderPage(roles: readonly string[]) {
  setSession({
    accessToken: "test-access-token",
    markets: [],
    principal: {
      userId: "33333333-3333-4333-8333-333333333333",
      phone: "+998900000000",
      fullName: "Test Foydalanuvchi",
      roles,
      marketId: MARKET_ID,
      marketName: "Karmana markaziy bozori",
      isPlatformAdmin: false,
      locale: "uz-Latn",
      mustChangePassword: false,
    },
  });

  return render(
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      now={NOW}
      timeZone={TIME_ZONE}
    >
      <NuqsTestingAdapter searchParams="">
        <QueryClientProvider client={client}>
          <AuthProvider>
            <CamerasPage />
          </AuthProvider>
        </QueryClientProvider>
      </NuqsTestingAdapter>
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
  client.clear();
  clearSession();
});

/* ---------------------------------------------------------------------------
 * DIREKTOR — `camera_view` BOR, `camera_manage` YO'Q
 * ------------------------------------------------------------------------ */

describe("direktor", () => {
  test("NVR kartasining UCHALA amali ham ko'rinmaydi", async () => {
    routeFetch();
    renderPage(["director"]);

    // Skelet o'tguncha kutamiz — karta chizilgandan KEYIN o'lchaymiz.
    await screen.findByText(messages.cameras.nvrCard);

    for (const label of MANAGE_LABELS) {
      expect(document.body.textContent).not.toContain(label);
    }
  });

  test("pasport va sahifa mazmuni QOLADI — sahifa bo'sh emas", async () => {
    routeFetch();
    renderPage(["director"]);

    await screen.findByText(messages.cameras.nvrCard);

    expect(document.body.textContent).toContain(DEVICE.host);
    expect(screen.getByText(messages.cameras.title)).toBeInTheDocument();
  });

  test("`camera-zones` ga so'rov YO'Q — qamrov `camera_manage` ostida", async () => {
    routeFetch();
    renderPage(["director"]);

    await screen.findByText(messages.cameras.nvrCard);

    expect(
      requestedPaths().filter((path) => path.includes("camera-zones")),
    ).toEqual([]);
  });
});

/* ---------------------------------------------------------------------------
 * BOZOR ADMINI — UCHALA AMAL HAM O'Z JOYIDA (regressiya qulfi)
 * ------------------------------------------------------------------------ */

describe("bozor admini", () => {
  test("uchala amal ham render qilinadi", async () => {
    routeFetch();
    renderPage(["market_admin"]);

    await screen.findByText(messages.cameras.nvrCard);

    for (const label of MANAGE_LABELS) {
      expect(screen.getByRole("button", { name: label })).toBeInTheDocument();
    }
  });

  test("qamrov kartasi so'raladi", async () => {
    routeFetch();
    renderPage(["market_admin"]);

    await waitFor(() => {
      expect(
        requestedPaths().some((path) => path.includes("camera-zones")),
      ).toBe(true);
    });
  });
});

/* ---------------------------------------------------------------------------
 * NAZORATCHI — `camera_view` YO'Q: HUQUQ TEKSHIRUVI SO'ROVDAN OLDIN
 * ------------------------------------------------------------------------ */

describe("nazoratchi", () => {
  test("rad etish ko'rinadi va `apiFetch` UMUMAN chaqirilmaydi", async () => {
    routeFetch();
    renderPage(["inspector"]);

    expect(screen.getByText(messages.errors.forbidden)).toBeInTheDocument();

    // Ish maydoni umuman mount qilinmaydi -> birorta so'rov ketmaydi.
    await waitFor(() => {
      expect(apiClientMock.apiFetch).not.toHaveBeenCalled();
    });
  });
});

/* ---------------------------------------------------------------------------
 * «DIAGNOSTIKA» TUGMASI -> DIAGNOSTIKA PANELI (Topilma №F)
 *
 * ⛔ BU YERDA HAM O'LCHANADIGAN NARSA — ULANISH, KOMPONENT EMAS.
 *
 *    `nvr-form.test.tsx` `mode` PROPI bo'yicha o'lchaydi, ya'ni forma
 *    rejimga bo'ysunishini isbotlaydi. Topilma №F esa aynan SHU YERDA
 *    tug'ilgan edi: `onDiagnose={() => setFormOpen(true)}` `NvrForm` ni
 *    ochardi va sahifa unga rejim UZATMASDI. Prop bo'yicha o'lchov bunday
 *    nosozlikni HECH QACHON ko'rmasdi.
 *
 * ⚠ IKKINCHI TEST — TESKARISI VA U MAJBURIY. Usiz «rejim uzatilyapti»
 *   da'vosi «forma HAR DOIM diagnostika rejimida» dan farqlanmasdi, ya'ni
 *   `mode` ni konstantaga qadash ham yashil qolardi.
 * ------------------------------------------------------------------------ */

describe("diagnostika rejimi (Topilma №F)", () => {
  test("«Diagnostika» bosilganda diagnostika legendasi ochiladi, «Saqlash…» YO'Q", async () => {
    routeFetch();
    renderPage(["market_admin"]);

    const diagnose = await screen.findByRole("button", {
      name: DIAGNOSTICS_LABEL,
    });
    fireEvent.click(diagnose);

    await screen.findByRole("group", { name: messages.cameras.diagnoseLegend });
    expect(document.body.textContent).not.toContain(
      messages.cameras.saveAndDiscover,
    );
  });

  test("NVR YO'Q sahifada «NVR ulash» AVVALGIDEK saqlash formasini ochadi", async () => {
    routeFetchWithoutDevice();
    renderPage(["market_admin"]);

    const connect = await screen.findByRole("button", {
      name: messages.cameras.connectNvr,
    });
    fireEvent.click(connect);

    await screen.findByRole("group", { name: messages.cameras.nvrLegend });
    expect(
      screen.getByRole("button", { name: messages.cameras.saveAndDiscover }),
    ).toBeInTheDocument();
    expect(document.body.textContent).not.toContain(
      messages.cameras.diagnoseLegend,
    );
  });
});
