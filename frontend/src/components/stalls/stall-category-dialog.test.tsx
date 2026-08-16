/**
 * RASTA TOIFASI DIALOGI — ⛔ TANLANMAGAN TOIFA SABABINI AYTADI (F-2).
 *
 * =============================================================================
 * BU FAYLNING MARKAZIY DA'VOSI:
 *
 *   Toifa tanlanmagan holda «Saqlash» BOSILADI va `errors.required`
 *   EKRANGA CHIQADI.
 *
 *   Ilgari tugma `disabled={categoryId === "" || isSubmitting}` edi —
 *   ya'ni aynan tuzatilishi kerak bo'lgan holatda bosilmasdi va zod
 *   xabari hech qachon ko'rinmasdi. Bu «jim-disabled submit» anti-naqshi
 *   (TEST-REPORT Topilma №4 sinfi), etaloni `create-user-dialog.tsx`.
 * =============================================================================
 *
 * ⚠ SANA MAYDONI OLDINDAN TO'LDIRILGAN (`reset` effekti, ertangi kun), ya'ni
 *   yagona bo'sh maydon — toifa. Testning da'vosi shu bilan tor: u AYNAN
 *   toifa xatosini o'lchaydi, «biror xato chiqdi» ni emas.
 *
 * DIQQAT: bosish `fireEvent` bilan — loyihada `user-event` ishlatilmaydi.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

const apiClientMock = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiClientMock.apiFetch };
});

import messages from "../../../messages/uz-Latn.json";
import { StallCategoryDialog } from "@/components/stalls/stall-category-dialog";
import type { StallListItem } from "@/lib/api-types";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const { apiFetch } = apiClientMock;

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const ZONE_ID = "22222222-2222-4222-8222-222222222222";
const CATEGORY_ID = "33333333-3333-4333-8333-333333333333";
const STALL_ID = "44444444-4444-4444-8444-444444444444";

const CATEGORY_NAME = "Sabzavotlar";

/** uz-Latn kataloglaridagi AYNAN qiymatlar. */
const SAVE = messages.common.save;
const REQUIRED = messages.errors.required;
const CATEGORY_LABEL = messages.stalls.categoryLabel;

/** `Field` ning `${id}-error` konvensiyasi (`ui/field.tsx`). */
const CATEGORY_ERROR_ID = "stall-category-value-error";

const CATEGORIES_PATH = "/categories";
const SET_CATEGORY_PATH = `/stalls/${STALL_ID}/category`;

const STALL: StallListItem = {
  id: STALL_ID,
  code: "12",
  zone_id: ZONE_ID,
  zone_name: "Shimoliy qator",
  category_id: null,
  category_name: null,
  status: "active",
  vendor_id: null,
  vendor_name: null,
  tariff_soum: null,
  created_at: "2026-08-16T05:00:00Z",
};

function seedSession(): void {
  setSession({
    accessToken: "test-access-token",
    principal: {
      userId: "55555555-5555-4555-8555-555555555555",
      phone: "+998900000000",
      fullName: "Test Admin",
      roles: ["market_admin"],
      marketId: MARKET_ID,
      marketName: "Karmana markaziy bozori",
      isPlatformAdmin: false,
      locale: "uz-Latn",
      mustChangePassword: false,
    },
    markets: [],
  });
}

function mockLookups(): void {
  apiFetch.mockImplementation((path: string) => {
    if (path === CATEGORIES_PATH) {
      return Promise.resolve({
        items: [{ id: CATEGORY_ID, name: CATEGORY_NAME }],
        next_cursor: null,
      });
    }
    if (path === SET_CATEGORY_PATH) return Promise.resolve({});
    return Promise.reject(new Error(`kutilmagan yo'l: ${path}`));
  });
}

function renderDialog(): void {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  const tree: ReactElement = (
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      timeZone="Asia/Tashkent"
    >
      <QueryClientProvider client={client}>
        <AuthProvider>
          <StallCategoryDialog onOpenChange={vi.fn()} open stall={STALL} />
        </AuthProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>
  );

  render(tree);
}

function clickSave(): void {
  fireEvent.click(screen.getByRole("button", { name: SAVE }));
}

/** `POST /stalls/{id}/category` chaqiruvlari — toifa GET'i sanoqqa kirmaydi. */
function setCategoryCalls(): unknown[][] {
  return apiFetch.mock.calls.filter(
    (args: unknown[]) => args[0] === SET_CATEGORY_PATH,
  );
}

beforeEach(() => {
  vi.resetAllMocks();
  clearSession();
  seedSession();
});

afterEach(() => {
  clearSession();
});

/* ---------------------------------------------------------------------------
 * ⛔ T1/T2 — TANLANMAGAN TOIFA KO'RINADIGAN XABAR BERADI
 * ------------------------------------------------------------------------ */

describe("toifa tanlanmagan holda saqlash", () => {
  test("⛔ `errors.required` EKRANDA ko'rinadi va maydonga bog'lanadi", async () => {
    mockLookups();
    renderDialog();
    await screen.findByRole("option", { name: CATEGORY_NAME });

    clickSave();

    await waitFor(() => {
      expect(document.getElementById(CATEGORY_ERROR_ID)).not.toBeNull();
    });
    expect(document.getElementById(CATEGORY_ERROR_ID)?.textContent).toBe(
      REQUIRED,
    );

    const select = screen.getByLabelText(CATEGORY_LABEL);
    expect(select).toHaveAttribute("aria-describedby", CATEGORY_ERROR_ID);
    expect(select).toHaveAttribute("aria-invalid", "true");
  });

  test("⛔ `POST /stalls/{id}/category` YUBORILMAYDI", async () => {
    mockLookups();
    renderDialog();
    await screen.findByRole("option", { name: CATEGORY_NAME });

    clickSave();

    await waitFor(() => {
      expect(document.getElementById(CATEGORY_ERROR_ID)).not.toBeNull();
    });
    expect(setCategoryCalls()).toHaveLength(0);
  });
});

/* ---------------------------------------------------------------------------
 * T3 — NAZORAT: TANLANGAN TOIFA AYNAN BITTA SO'ROV YUBORADI
 * ------------------------------------------------------------------------ */

describe("tanlangan toifa (nazorat)", () => {
  test("AYNAN BITTA so'rov ketadi, tanasida `category_id` va `valid_from` bor", async () => {
    mockLookups();
    renderDialog();
    await screen.findByRole("option", { name: CATEGORY_NAME });

    fireEvent.change(screen.getByLabelText(CATEGORY_LABEL), {
      target: { value: CATEGORY_ID },
    });
    clickSave();

    await waitFor(() => {
      expect(setCategoryCalls()).toHaveLength(1);
    });

    const options = setCategoryCalls()[0][1] as {
      body: Record<string, unknown>;
      method: string;
    };
    expect(options.method).toBe("POST");
    expect(options.body.category_id).toBe(CATEGORY_ID);
    /*
     * Sana OLDINDAN to'ldirilgan (ertangi kun, bozor mintaqasida) — test
     * uni QAYTA HISOBLAMAYDI, faqat mavjudligi va ISO shaklini o'lchaydi.
     * Qiymatni bu yerda ikkinchi marta hisoblash `tomorrowIn()` ning
     * nusxasini yaratardi va ular bir kun ajralib ketardi.
     */
    expect(options.body.valid_from).toMatch(/^\d{4}-\d{2}-\d{2}$/u);
  });
});
