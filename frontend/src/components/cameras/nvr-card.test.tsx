/**
 * NVR KARTASI — UCHTA AMAL `camera_manage` OSTIDA (Topilma №J).
 *
 * =============================================================================
 * BU FAYLNING MARKAZIY DA'VOSI:
 *
 *   KARTA HUQUQ KO'ZGUSI: `canManage: false` da UCHALA AMAL HAM YO'Q,
 *   PASPORT esa QOLADI.
 *
 *   Direktorda `camera_view` bor, `camera_manage` YO'Q (`rbac.ts`), ya'ni
 *   u NVR pasportini KO'RISHI kerak, lekin «Qayta skanerlash», «Parolni
 *   yangilash» va «Diagnostika» ni bosa OLMAYDI — backend uchalasini ham
 *   `require_permission(CAMERA_MANAGE)` bilan rad etadi (`nvr.py:372,482,536`).
 *   Tugmani ko'rsatib turib 403 berish «tizim menga nimadir va'da qildi va
 *   aldadi» ta'surotini beradi.
 *
 * ⛔ IKKI YO'NALISHDA HAM O'LCHANADI. Faqat «yo'q» ni tekshirish kartani
 *    bo'shatib qo'yish bilan ham yashil bo'lardi; shuning uchun HAR
 *    yo'qlik da'vosining yonida `camera_view` mazmuni QOLGANINI
 *    tasdiqlaydigan assert turadi.
 *
 * ⚠ BU FAYL KOMPONENTNI O'LCHAYDI, WIRING NI EMAS. Sahifa `canManage` ni
 *   haqiqiy roldan hosil qiladimi — bu `app/[locale]/(app)/cameras/
 *   page.test.tsx` ning da'vosi. Ikkalasi ATAYIN ajratilgan: rejadagi
 *   sabotaj o'lchovi (`canManage={true}`) aynan shu faylni YASHIL
 *   qoldirib, sahifa testini qizartirishi kerak.
 *
 * ⚠ QULFLOVCHI KOD REYESTRDAN olinadi (`AUTH_LOCKING_CODES[0]`), literal
 *   yozilmaydi (05-13 darsi: literal reyestr o'zgarganda jimgina
 *   eskirardi). Massivning bo'sh emasligi ALOHIDA assert bilan
 *   tasdiqlanadi — aks holda `[0]` `undefined` bo'lib, qulf umuman
 *   armlanmasdi va test o'z-o'zidan yashil qolardi.
 * =============================================================================
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

const apiClientMock = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiClientMock.apiFetch };
});

vi.mock("sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}));

import messages from "../../../messages/uz-Latn.json";
import { NvrCard } from "@/components/cameras/nvr-card";
import type { NvrDevice } from "@/lib/api-types";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";
import { AUTH_LOCKING_CODES } from "@/lib/nvr-errors";

/** uz-Latn katalogidagi AYNAN qiymatlar — literal satr YOZILMAYDI. */
const RESCAN_LABEL = messages.cameras.rescan;
const PASSWORD_LABEL = messages.cameras.updatePassword;
const DIAGNOSTICS_LABEL = messages.cameras.diagnostics;
const AUTH_LOCK_HINT = messages.cameras.authLockHint;
const LAST_SCAN_LABEL = messages.cameras.lastScan;

const MANAGE_LABELS = [RESCAN_LABEL, PASSWORD_LABEL, DIAGNOSTICS_LABEL];

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const TIME_ZONE = "Asia/Tashkent";
const NOW = new Date("2026-08-16T09:00:00Z");

/** `nvrDeviceSchema` ning O'N TO'RTALA maydoni (`api-types.ts:889-904`). */
function makeDevice(overrides: Partial<NvrDevice> = {}): NvrDevice {
  return {
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
    ...overrides,
  };
}

let client: QueryClient;

function renderCard(options: {
  canManage: boolean;
  device?: NvrDevice;
  errorCode?: string | null;
}): void {
  const tree: ReactElement = (
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      now={NOW}
      timeZone={TIME_ZONE}
    >
      <QueryClientProvider client={client}>
        <AuthProvider>
          <NvrCard
            canManage={options.canManage}
            device={options.device ?? makeDevice()}
            errorCode={options.errorCode ?? null}
            onDiagnose={vi.fn()}
            onRescan={vi.fn()}
          />
        </AuthProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>
  );

  render(tree);
}

beforeEach(() => {
  vi.resetAllMocks();
  client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  /*
   * Bozorsiz sessiyada `NvrPasswordDialog` ichidagi `useUpdateNvrPassword`
   * kalit qurishda `marketId` ni topolmasdi — dialog `canManage: true`
   * shoxida MOUNT QILINADI, ya'ni sessiya bu yerda MAJBURIY.
   */
  setSession({
    accessToken: "test-access-token",
    markets: [],
    principal: {
      userId: "33333333-3333-4333-8333-333333333333",
      phone: "+998900000000",
      fullName: "Test Admin",
      roles: ["market_admin"],
      marketId: MARKET_ID,
      marketName: "Karmana markaziy bozori",
      isPlatformAdmin: false,
      locale: "uz-Latn",
      mustChangePassword: false,
    },
  });
});

afterEach(() => {
  client.clear();
  clearSession();
});

/* ---------------------------------------------------------------------------
 * NAZORAT: reyestr bo'sh emas — usiz qulf da'vosi o'z-o'zidan yashil qolardi
 * ------------------------------------------------------------------------ */

test("nazorat: `AUTH_LOCKING_CODES` bo'sh EMAS", () => {
  expect(AUTH_LOCKING_CODES.length).toBeGreaterThan(0);
});

/* ---------------------------------------------------------------------------
 * `canManage: true` — BUGUNGI XULQ, REGRESSIYA QULFI
 * ------------------------------------------------------------------------ */

describe("`camera_manage` BOR", () => {
  test("uchala amal ham render qilinadi", () => {
    renderCard({ canManage: true });

    for (const label of MANAGE_LABELS) {
      expect(screen.getByRole("button", { name: label })).toBeInTheDocument();
    }
  });

  test("auth qulfi «Qayta skanerlash» ni bloklaydi va izohini beradi", () => {
    renderCard({ canManage: true, errorCode: AUTH_LOCKING_CODES[0] });

    expect(screen.getByRole("button", { name: RESCAN_LABEL })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
    expect(screen.getByRole("status")).toHaveTextContent(AUTH_LOCK_HINT);

    /*
     * «Parolni yangilash» qulf OSTIDA HAM ochiq qoladi — u qulfdan
     * chiqishning yagona yo'li (§4.4). Bu shox `canManage` bilan
     * o'zgarmasligi kerak.
     */
    expect(
      screen.getByRole("button", { name: PASSWORD_LABEL }),
    ).not.toHaveAttribute("aria-disabled");
  });
});

/* ---------------------------------------------------------------------------
 * `canManage: false` — TOPILMA №J NING O'ZI
 * ------------------------------------------------------------------------ */

describe("`camera_manage` YO'Q (direktor)", () => {
  test("uchala amal ham YO'Q — rol bo'yicha ham, MATN bo'yicha ham", () => {
    renderCard({ canManage: false });

    for (const label of MANAGE_LABELS) {
      expect(screen.queryByRole("button", { name: label })).toBeNull();
      // Yashirilgan (lekin DOM'da qolgan) tugma birinchi assertdan
      // o'tib ketardi — matn bo'yicha ikkinchi kanal shuning uchun.
      expect(document.body.textContent).not.toContain(label);
    }
  });

  test("PASPORT QOLADI — `camera_view` mazmuni yo'qotilmaydi", () => {
    const device = makeDevice();
    renderCard({ canManage: false, device });

    expect(document.body.textContent).toContain(device.host);
    expect(document.body.textContent).toContain(device.firmware_version ?? "");
    expect(document.body.textContent).toContain(device.serial_number ?? "");
    expect(screen.getByText(LAST_SCAN_LABEL)).toBeInTheDocument();
    expect(screen.getByText(messages.cameras.nvrCard)).toBeInTheDocument();
  });

  test("qulf izohi CHIZILMAYDI — u mavjud bo'lmagan tugmaga yo'naltirardi", () => {
    renderCard({ canManage: false, errorCode: AUTH_LOCKING_CODES[0] });

    expect(screen.queryByText(AUTH_LOCK_HINT)).toBeNull();
    expect(document.body.textContent).not.toContain(AUTH_LOCK_HINT);
  });
});
