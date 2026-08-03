/**
 * NVR FORMASI — MANZIL AJRATISH JADVALI VA AUTH QULFI.
 *
 * =============================================================================
 * IKKI GURUH, IKKI XIL DA'VO:
 *
 *   (a) AJRATISH JADVALI (UI-SPEC §4.1). Ekranda uchta maydon turishi
 *       D-01 ning butun mazmuni; port va TLS esa manzildan ajratiladi.
 *       Jadvalning oltala qatori sof funksiya ustida o'lchanadi —
 *       ajratish serverdagi `nvr_host.split_address()` ning ko'zgusi va
 *       ikkovi bir kun ajralib ketsa bu yerda ko'rinadi.
 *
 *   (b) AUTH QULFI (UI-SPEC §4.4, D-03). Bu — fazaning eng muhim
 *       interaksiya qoidasi va uni FAQAT DOM darajasida o'lchash mumkin:
 *       tugmaning bloklanishi, so'rovning YUBORILMASLIGI, fokusning
 *       parol maydoniga ko'chishi va — eng muhimi — qulfning FAQAT
 *       rekvizit qiymati o'zgarganda ochilishi.
 *
 * ⚠ (b) NING OXIRGI BANDI ENG MUHIM ASSERT. Usiz «qulf ishlaydi»
 *   da'vosi «qulf BIR MARTA ishladi» dan farqlanmasdi: tugmani qayta
 *   bosish qulfni ochib yuborsa, admin uch bosishda hisobni 30 daqiqaga
 *   qulflardi va D-03 ning butun mazmuni yo'qolardi.
 *
 * DIQQAT: bosish `fireEvent` bilan qilinadi, `@testing-library/user-event`
 * bilan EMAS — `market-picker.test.tsx` dagi bilan bir xil sabab
 * (tasdiqlangan paket ro'yxatiga kirmaydi).
 * =============================================================================
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import { NvrForm, splitNvrAddress } from "@/components/cameras/nvr-form";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const apiClientMock = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiClientMock.apiFetch };
});

vi.mock("sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}));

const { apiFetch } = apiClientMock;

const MARKET_ID = "11111111-1111-4111-8111-111111111111";

/** uz-Latn kataloglaridagi AYNAN qiymatlar. */
const ADDRESS_LABEL = messages.cameras.nvrAddress;
const LOGIN_LABEL = messages.cameras.nvrLogin;
const PASSWORD_LABEL = messages.cameras.nvrPassword;
const SAVE_LABEL = messages.cameras.saveAndDiscover;
const TEST_LABEL = messages.cameras.testConnection;
const SHOW_PASSWORD_LABEL = messages.cameras.showPassword;
const HIDE_PASSWORD_LABEL = messages.cameras.hidePassword;
const AUTH_LOCK_HINT = messages.cameras.authLockHint;
const RETRY_LABEL = messages.cameras.retryCheck;
const PUBLIC_BLOCKED = messages.cameras.publicAddressBlocked;
const INVALID_PORT = messages.cameras.invalidPort;

/* ---------------------------------------------------------------------------
 * (a) MANZILNI AJRATISH — UI-SPEC §4.1 jadvalining OLTALA qatori
 * ------------------------------------------------------------------------ */

describe("splitNvrAddress — UI-SPEC §4.1 jadvali", () => {
  test.each([
    ["192.168.1.64", "192.168.1.64", 80, false],
    ["192.168.1.64:8080", "192.168.1.64", 8080, false],
    ["http://192.168.1.64", "192.168.1.64", 80, false],
    ["https://192.168.1.64", "192.168.1.64", 443, true],
    ["https://192.168.1.64:8443", "192.168.1.64", 8443, true],
    ["nvr.local", "nvr.local", 80, false],
  ])("%s -> %s:%i (tls=%s)", (input, host, port, useTls) => {
    const result = splitNvrAddress(input);

    expect(result.kind).toBe("ok");
    if (result.kind !== "ok") return;
    expect(result.parts).toEqual({ host, port, use_tls: useTls });
  });

  test("ommaviy IP rad etiladi, xususiy va CGNAT esa o'tadi", () => {
    expect(splitNvrAddress("8.8.8.8").kind).toBe("public_blocked");
    expect(splitNvrAddress("203.0.114.7").kind).toBe("public_blocked");

    // ⚠ CGNAT — `is_global` va «xususiy emas» ni AJRATADIGAN yagona
    //   holat (03-04 da o'lchangan). U bozor tomonidagi operator
    //   tarmog'ida uchraydi va O'TISHI SHART.
    expect(splitNvrAddress("100.100.1.5").kind).toBe("ok");
    expect(splitNvrAddress("10.0.0.5").kind).toBe("ok");
    expect(splitNvrAddress("172.20.3.4").kind).toBe("ok");
    // Hujjatlashtirish uchun ajratilgan blok — marshrutlanmaydi.
    expect(splitNvrAddress("203.0.113.7").kind).toBe("ok");
  });

  test("port oralig'i 1..65535", () => {
    expect(splitNvrAddress("192.168.1.64:0").kind).toBe("invalid_port");
    expect(splitNvrAddress("192.168.1.64:70000").kind).toBe("invalid_port");
    expect(splitNvrAddress("192.168.1.64:abc").kind).toBe("invalid_port");
    expect(splitNvrAddress("192.168.1.64:65535").kind).toBe("ok");
  });

  test("qo'llab-quvvatlanmaydigan sxema va bo'sh qiymat rad etiladi", () => {
    expect(splitNvrAddress("").kind).toBe("invalid_address");
    expect(splitNvrAddress("   ").kind).toBe("invalid_address");
    expect(splitNvrAddress("ftp://192.168.1.64").kind).toBe("invalid_address");
    expect(splitNvrAddress("192.168.1.64 64").kind).toBe("invalid_address");
  });

  test("yo'l qismi tashlanadi (brauzerdan ko'chirilgan manzil)", () => {
    const result = splitNvrAddress("https://nvr.local:8443/doc/index.html");

    expect(result.kind).toBe("ok");
    if (result.kind !== "ok") return;
    expect(result.parts).toEqual({ host: "nvr.local", port: 8443, use_tls: true });
  });
});

/* ---------------------------------------------------------------------------
 * DOM — forma
 * ------------------------------------------------------------------------ */

function renderForm(): ReturnType<typeof render> {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false }, queries: { retry: false } },
  });

  const tree: ReactElement = (
    <NextIntlClientProvider locale="uz-Latn" messages={messages}>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <NvrForm />
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

function addressInput(): HTMLInputElement {
  return screen.getByLabelText(ADDRESS_LABEL) as HTMLInputElement;
}

function loginInput(): HTMLInputElement {
  return screen.getByLabelText(LOGIN_LABEL) as HTMLInputElement;
}

function passwordInput(): HTMLInputElement {
  return screen.getByLabelText(PASSWORD_LABEL) as HTMLInputElement;
}

/**
 * Birlamchi tugma — TIP bo'yicha topiladi, MATN bo'yicha emas.
 *
 * ⚠ Sabab o'lchangan: yuborish paytida tugma matni almashadi (UI-SPEC
 *   §4.3) va nomga qadalgan so'rov AYNAN o'sha lahzada tugmani topa
 *   olmasdi — ya'ni «uch marta bosish» testi qoidani emas, matnning
 *   almashish tezligini o'lchab qolardi.
 */
function saveButton(): HTMLButtonElement {
  const node = document.querySelector<HTMLButtonElement>(
    'button[type="submit"]',
  );
  if (node === null) throw new Error("birlamchi tugma topilmadi");
  return node;
}

function testButton(): HTMLElement {
  return screen.getByRole("button", { name: TEST_LABEL });
}

function fillCredentials(password = "wrong-password"): void {
  fireEvent.change(addressInput(), { target: { value: "192.168.1.64" } });
  fireEvent.change(loginInput(), { target: { value: "admin" } });
  fireEvent.change(passwordInput(), { target: { value: password } });
}

/** `test-connection` HAR DOIM 200 qaytaradi — xato javob TANASIDA. */
function mockAuthFailure(): void {
  apiFetch.mockResolvedValue({
    auth_locked: true,
    error_code: "nvr_bad_credentials",
    error_detail: null,
    ok: false,
    rtsp_port_assumed: false,
  });
}

/** Formani qulflangan holatga keltiradi. */
async function lockForm(): Promise<void> {
  mockAuthFailure();
  fillCredentials();
  fireEvent.click(testButton());

  await waitFor(() => {
    expect(screen.getByRole("status")).toHaveTextContent(AUTH_LOCK_HINT);
  });
}

describe("NvrForm — uchta maydon va parol (D-01, D-12)", () => {
  beforeEach(() => {
    apiFetch.mockReset();
    clearSession();
    seedSession();
  });

  afterEach(() => {
    clearSession();
  });

  test("AYNAN uchta maydon: port va TLS uchun alohida maydon YO'Q", () => {
    renderForm();

    const group = screen.getByRole("group", { name: messages.cameras.nvrLegend });
    const controls = group.querySelectorAll("input");

    expect(controls).toHaveLength(3);
    expect(addressInput()).toBeInTheDocument();
    expect(loginInput()).toBeInTheDocument();
    expect(passwordInput()).toBeInTheDocument();

    // Ikkita tugma va ikkalasi ham kerak (§4.3) — tekshiruv MAJBURIY EMAS.
    expect(screen.getByRole("button", { name: SAVE_LABEL })).toBe(saveButton());
    expect(testButton()).toBeInTheDocument();
  });

  test("parol maydoni yopiq va brauzer parol menejeriga tushmaydi", () => {
    renderForm();

    expect(passwordInput().type).toBe("password");
    expect(passwordInput().getAttribute("autocomplete")).toBe("new-password");
    // Forma parolni HECH QACHON so'ramaydi — boshlang'ich qiymat bo'sh.
    expect(passwordInput().value).toBe("");
  });

  test("ko'rsatish tugmasida `aria-pressed` VA o'zgaruvchan `aria-label`", () => {
    renderForm();

    const toggle = screen.getByRole("button", { name: SHOW_PASSWORD_LABEL });
    expect(toggle).toHaveAttribute("aria-pressed", "false");

    fireEvent.click(toggle);

    expect(passwordInput().type).toBe("text");
    const pressed = screen.getByRole("button", { name: HIDE_PASSWORD_LABEL });
    expect(pressed).toHaveAttribute("aria-pressed", "true");
  });

  test("ommaviy IP maydon OSTIDA tushuntirish bilan to'xtatiladi", async () => {
    renderForm();

    fireEvent.change(addressInput(), { target: { value: "8.8.8.8" } });
    fireEvent.change(loginInput(), { target: { value: "admin" } });
    fireEvent.change(passwordInput(), { target: { value: "secret" } });
    fireEvent.click(saveButton());

    await waitFor(() => {
      expect(screen.getByText(PUBLIC_BLOCKED)).toBeInTheDocument();
    });

    // ⚠ SO'ROV UMUMAN YUBORILMAYDI: server darvozasi (`assert_private_host`)
    //   baribir rad etardi, lekin sabab yo'qolardi.
    expect(apiFetch).not.toHaveBeenCalled();
    expect(screen.getByText(PUBLIC_BLOCKED).id).toBe("nvr-address-error");
  });

  test("port oralig'i buzilganda BOSHQA matn chiqadi", async () => {
    renderForm();

    fireEvent.change(addressInput(), { target: { value: "192.168.1.64:70000" } });
    fireEvent.change(loginInput(), { target: { value: "admin" } });
    fireEvent.change(passwordInput(), { target: { value: "secret" } });
    fireEvent.click(saveButton());

    await waitFor(() => {
      expect(screen.getByText(INVALID_PORT)).toBeInTheDocument();
    });
    expect(apiFetch).not.toHaveBeenCalled();
  });
});

/* ---------------------------------------------------------------------------
 * (b) AUTH QULFI — D-03 ning UI tarjimasi
 * ------------------------------------------------------------------------ */

describe("NvrForm — auth qulfi (UI-SPEC §4.4, D-03)", () => {
  beforeEach(() => {
    apiFetch.mockReset();
    clearSession();
    seedSession();
  });

  afterEach(() => {
    clearSession();
  });

  test("qulflovchi kod kelganda IKKALA tugma ham bloklanadi", async () => {
    renderForm();
    await lockForm();

    expect(saveButton()).toHaveAttribute("aria-disabled", "true");
    expect(testButton()).toHaveAttribute("aria-disabled", "true");

    // Birlamchi tugma `secondary` ga o'tadi — aksent budjeti (§2.4).
    expect(saveButton().className).not.toContain("bg-accent");
  });

  test("xato blokida qayta urinish affordansi RENDER QILINMAYDI", async () => {
    renderForm();
    await lockForm();

    expect(screen.queryByRole("button", { name: RETRY_LABEL })).toBeNull();
    expect(document.body.textContent).not.toContain(RETRY_LABEL);
  });

  test("bloklangan tugma bosilganda SO'ROV YUBORILMAYDI, fokus parolga ko'chadi", async () => {
    renderForm();
    await lockForm();

    apiFetch.mockClear();
    fireEvent.click(saveButton());

    await waitFor(() => {
      expect(document.activeElement).toBe(passwordInput());
    });
    expect(apiFetch).not.toHaveBeenCalled();

    // Ikkinchi tugma ham xuddi shunday.
    fireEvent.click(testButton());
    await waitFor(() => {
      expect(document.activeElement).toBe(passwordInput());
    });
    expect(apiFetch).not.toHaveBeenCalled();
  });

  test("⚠ TUGMANI QAYTA BOSISH QULFNI OCHMAYDI", async () => {
    /*
     * ENG MUHIM ASSERT. Qulf ochilishi tugmaga bog'langan bo'lsa,
     * quyidagi uch bosish uni ochib yuborardi va admin uchinchi
     * urinishda NVR hisobini 30 daqiqaga qulflardi.
     */
    renderForm();
    await lockForm();

    apiFetch.mockClear();
    fireEvent.click(saveButton());
    fireEvent.click(saveButton());
    fireEvent.click(testButton());

    await waitFor(() => {
      expect(document.activeElement).toBe(passwordInput());
    });

    expect(saveButton()).toHaveAttribute("aria-disabled", "true");
    expect(testButton()).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByRole("status")).toHaveTextContent(AUTH_LOCK_HINT);
    expect(apiFetch).not.toHaveBeenCalled();
  });

  test("qulf PAROL qiymati o'zgarganda ochiladi", async () => {
    renderForm();
    await lockForm();

    fireEvent.change(passwordInput(), { target: { value: "another-password" } });

    await waitFor(() => {
      expect(saveButton()).not.toHaveAttribute("aria-disabled");
    });
    expect(testButton()).not.toHaveAttribute("aria-disabled");
    expect(screen.queryByRole("status")).toBeNull();
  });

  test("qulf LOGIN qiymati o'zgarganda ham ochiladi", async () => {
    renderForm();
    await lockForm();

    fireEvent.change(loginInput(), { target: { value: "operator" } });

    await waitFor(() => {
      expect(saveButton()).not.toHaveAttribute("aria-disabled");
    });
  });

  test("qulf ochilgandan keyin so'rov YANA yuboriladi", async () => {
    renderForm();
    await lockForm();

    apiFetch.mockClear();
    apiFetch.mockResolvedValue({
      auth_locked: false,
      channels_preview: 6,
      clock_drift_seconds: 12,
      device_type: "NVR",
      model: "DS-7616NI-K2",
      ok: true,
      rtsp_port_assumed: false,
    });

    fireEvent.change(passwordInput(), { target: { value: "correct-password" } });
    await waitFor(() => {
      expect(saveButton()).not.toHaveAttribute("aria-disabled");
    });

    fireEvent.click(testButton());

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/nvr-devices/test-connection",
        expect.objectContaining({ method: "POST" }),
      );
    });

    // Muvaffaqiyat bloki: kanallar soni VA soat farqi — ikkalasi ham.
    await waitFor(() => {
      expect(screen.getByText(messages.cameras.deviceFound)).toBeInTheDocument();
    });
    expect(screen.getByText("6 ta")).toBeInTheDocument();
    expect(screen.getByText("12 soniya")).toBeInTheDocument();
  });

  test("QULFLAMAYDIGAN xatoda tugmalar ochiq qoladi va retry BOR", async () => {
    /*
     * NAZORAT: qulf HAR xatoda emas, faqat `AUTH_LOCKING_CODES` da
     * yoqiladi. Usiz «qulf ishlaydi» da'vosi «hamma narsa bloklanadi»
     * dan farqlanmasdi.
     */
    apiFetch.mockResolvedValue({
      auth_locked: false,
      error_code: "nvr_clock_drift",
      error_detail: { drift_seconds: 420 },
      ok: false,
      rtsp_port_assumed: false,
    });

    renderForm();
    fillCredentials("secret");
    fireEvent.click(testButton());

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    expect(saveButton()).not.toHaveAttribute("aria-disabled");
    expect(screen.getByRole("button", { name: RETRY_LABEL })).toBeInTheDocument();
    expect(screen.queryByRole("status")).toBeNull();
  });
});

/* ---------------------------------------------------------------------------
 * Saqlash oqimi — parol forma holatidan CHIQADI (D-12)
 * ------------------------------------------------------------------------ */

describe("NvrForm — saqlash va kashfiyot", () => {
  beforeEach(() => {
    apiFetch.mockReset();
    clearSession();
    seedSession();
  });

  afterEach(() => {
    clearSession();
  });

  test("saqlash -> kashfiyot zanjiri va parolning tozalanishi", async () => {
    const deviceId = "55555555-5555-4555-8555-555555555555";
    const runId = "66666666-6666-4666-8666-666666666666";

    apiFetch.mockImplementation((path: string) => {
      if (path === "/nvr-devices") {
        return Promise.resolve({ has_password: true, id: deviceId });
      }
      if (path === `/nvr-devices/${deviceId}/discover`) {
        return Promise.resolve({ run_id: runId });
      }
      return Promise.reject(new Error(`kutilmagan yo'l: ${path}`));
    });

    renderForm();
    fillCredentials("correct-password");
    fireEvent.click(saveButton());

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        `/nvr-devices/${deviceId}/discover`,
        expect.objectContaining({ method: "POST" }),
      );
    });

    // ⚠ D-12: parol forma holatidan DARHOL chiqadi.
    await waitFor(() => {
      expect(passwordInput().value).toBe("");
    });
    // …manzil va login esa QOLADI — admin ularni qayta yozmaydi.
    expect(addressInput().value).toBe("192.168.1.64");
    expect(loginInput().value).toBe("admin");
  });

  test("serverga XOM `address` yuboriladi (ajratish serverning kontrakti)", async () => {
    apiFetch.mockResolvedValue({ has_password: true, id: "x" });

    renderForm();
    fireEvent.change(addressInput(), { target: { value: "192.168.1.64:8080" } });
    fireEvent.change(loginInput(), { target: { value: "admin" } });
    fireEvent.change(passwordInput(), { target: { value: "secret" } });
    fireEvent.click(saveButton());

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/nvr-devices",
        expect.objectContaining({
          body: {
            address: "192.168.1.64:8080",
            password: "secret",
            username: "admin",
          },
        }),
      );
    });
  });
});
