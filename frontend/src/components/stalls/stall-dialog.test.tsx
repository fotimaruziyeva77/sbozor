/**
 * RASTA DIALOGI — ⛔ O'CHIRILGAN TUGMA VALIDATSIYANING O'RNINI BOSMAYDI (F-1).
 *
 * =============================================================================
 * BU FAYLNING MARKAZIY DA'VOSI (TEST-REPORT Topilma №4 ning sinfi):
 *
 *   Rasta raqami bo'sh bo'lganda «Saqlash» BOSILADI va zodning
 *   `errors.required` xabari EKRANGA CHIQADI.
 *
 *   Ilgari tugma `disabled={code.trim() === "" || …}` edi. U «himoya»
 *   ko'rinishida edi, aslida esa xabarni ko'rsatishning YAGONA yo'lini
 *   yopib turardi: `handleSubmit` umuman chaqirilmasdi. Foydalanuvchi
 *   uchun «so'rov ketmadi + xato yo'q + dialog ochiq» uchligi
 *   «saqlandi, dialog yopilmadi» dan farqlanmaydi.
 *
 *   Etalon — `create-user-dialog.tsx`: `disabled={isSubmitting}`.
 * =============================================================================
 *
 * ⚠ T4 — CHEGARA. Tahrir rejimidagi `detail === undefined` qulfi ATAYIN
 *   SAQLANADI: urug'lanmagan forma mavjud izohni jimgina o'chirardi. U
 *   boshqa masala (tri-state) va uning yopilish tetigi — 260816-5yz.
 *   Bu test o'sha chegarani muzlatadi: tuzatish undan oshib ketmasin.
 *
 * ⚠ T3 — QULF HADDAN TASHQARI OCHILIB KETMAGANIGA nazorat: to'g'ri
 *   to'ldirilgan formada AYNAN BITTA `POST /stalls` ketadi va `code`
 *   trim qilinadi.
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
import { StallDialog } from "@/components/stalls/stall-dialog";
import type { StallDialogMode } from "@/components/stalls/stall-dialog";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const { apiFetch } = apiClientMock;

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const ZONE_ID = "22222222-2222-4222-8222-222222222222";
const CATEGORY_ID = "33333333-3333-4333-8333-333333333333";
const STALL_ID = "44444444-4444-4444-8444-444444444444";

/** DB kontenti — ATAYIN farqli nomlar: `getByRole("option")` noaniq bo'lmasin. */
const ZONE_NAME = "Shimoliy qator";
const CATEGORY_NAME = "Sabzavotlar";

/** uz-Latn kataloglaridagi AYNAN qiymatlar. */
const SAVE = messages.common.save;
const REQUIRED = messages.errors.required;
const CODE_LABEL = messages.stalls.codeLabel;
const ZONE_LABEL = messages.stalls.zoneLabel;
const CATEGORY_LABEL = messages.stalls.categoryLabel;

/** `Field` ning `${id}-error` konvensiyasi (`ui/field.tsx`). */
const CODE_ERROR_ID = "stall-form-code-error";

const ZONES_PATH = "/zones";
const CATEGORIES_PATH = "/categories";
const STALLS_PATH = "/stalls";
const STALL_DETAIL_PATH = `${STALLS_PATH}/${STALL_ID}`;

const CREATED_STALL = {
  id: STALL_ID,
  code: "12",
  zone_id: ZONE_ID,
  zone_name: ZONE_NAME,
  category_id: CATEGORY_ID,
  category_name: CATEGORY_NAME,
  status: "active",
  vendor_id: null,
  vendor_name: null,
  tariff_soum: null,
  created_at: "2026-08-16T05:00:00Z",
  phone: null,
  assignment_from: null,
  note: null,
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

/**
 * Ma'lumotnomalar HAR DOIM javob beradi; yozuv yo'li testga qoldiriladi.
 *
 * `apiFetch` TO'LIQ mock, ya'ni javob sxemasi qo'llanilmaydi — oddiy obyekt
 * yetarli.
 */
function mockLookups(): void {
  apiFetch.mockImplementation((path: string) => {
    if (path === ZONES_PATH) {
      return Promise.resolve({
        items: [{ id: ZONE_ID, name: ZONE_NAME }],
        next_cursor: null,
      });
    }
    if (path === CATEGORIES_PATH) {
      return Promise.resolve({
        items: [{ id: CATEGORY_ID, name: CATEGORY_NAME }],
        next_cursor: null,
      });
    }
    if (path === STALLS_PATH) return Promise.resolve(CREATED_STALL);
    return Promise.reject(new Error(`kutilmagan yo'l: ${path}`));
  });
}

function renderDialog(
  mode: StallDialogMode = "create",
  stallId: string | null = null,
): void {
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
          <StallDialog
            mode={mode}
            onOpenChange={vi.fn()}
            open
            stallId={stallId}
          />
        </AuthProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>
  );

  render(tree);
}

/** Zona va toifa TANLANADI — ya'ni yagona bo'sh maydon rasta raqami bo'ladi. */
async function chooseZoneAndCategory(): Promise<void> {
  await screen.findByRole("option", { name: ZONE_NAME });

  fireEvent.change(screen.getByLabelText(ZONE_LABEL), {
    target: { value: ZONE_ID },
  });
  fireEvent.change(screen.getByLabelText(CATEGORY_LABEL), {
    target: { value: CATEGORY_ID },
  });
}

function clickSave(): void {
  fireEvent.click(screen.getByRole("button", { name: SAVE }));
}

/** `POST /stalls` chaqiruvlari — ma'lumotnoma GET'lari sanoqqa kirmaydi. */
function createCalls(): unknown[][] {
  return apiFetch.mock.calls.filter(
    (args: unknown[]) =>
      args[0] === STALLS_PATH &&
      (args[1] as { method?: string } | undefined)?.method === "POST",
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
 * ⛔ T1 — BO'SH RASTA RAQAMI KO'RINADIGAN XABAR BERADI
 * ------------------------------------------------------------------------ */

describe("bo'sh rasta raqami bilan saqlash", () => {
  test("⛔ `errors.required` EKRANDA ko'rinadi", async () => {
    mockLookups();
    renderDialog();
    await chooseZoneAndCategory();

    clickSave();

    await waitFor(() => {
      expect(document.getElementById(CODE_ERROR_ID)).not.toBeNull();
    });
    expect(document.getElementById(CODE_ERROR_ID)?.textContent).toBe(REQUIRED);
  });

  test("⛔ xabar maydonga DASTURIY bog'lanadi", async () => {
    mockLookups();
    renderDialog();
    await chooseZoneAndCategory();

    clickSave();

    await waitFor(() => {
      expect(document.getElementById(CODE_ERROR_ID)).not.toBeNull();
    });

    /*
     * `role="alert"` BU YERDA TALAB QILINMAYDI: `Field` uni qo'ymaydi va
     * qo'yish ilovadagi HAR forma xatosini e'longa aylantirardi. Shartnoma
     * — ko'rinadigan matn + `${id}-error` + `aria-describedby` +
     * `aria-invalid` (etalonning telefon maydoni bilan bir xil).
     */
    const input = screen.getByLabelText(CODE_LABEL);
    expect(input).toHaveAttribute("aria-describedby", CODE_ERROR_ID);
    expect(input).toHaveAttribute("aria-invalid", "true");
  });

  test("⛔ `POST /stalls` YUBORILMAYDI — qulf saqlanadi", async () => {
    mockLookups();
    renderDialog();
    await chooseZoneAndCategory();

    clickSave();

    await waitFor(() => {
      expect(document.getElementById(CODE_ERROR_ID)).not.toBeNull();
    });
    expect(createCalls()).toHaveLength(0);
  });
});

/* ---------------------------------------------------------------------------
 * T3 — NAZORAT: TO'LIQ FORMA AYNAN BITTA SO'ROV YUBORADI
 * ------------------------------------------------------------------------ */

describe("to'ldirilgan forma (nazorat)", () => {
  test("AYNAN BITTA `POST /stalls` ketadi va `code` trim qilinadi", async () => {
    mockLookups();
    renderDialog();
    await chooseZoneAndCategory();

    fireEvent.change(screen.getByLabelText(CODE_LABEL), {
      target: { value: "  12  " },
    });
    clickSave();

    await waitFor(() => {
      expect(createCalls()).toHaveLength(1);
    });

    const options = createCalls()[0][1] as { body: Record<string, unknown> };
    expect(options.body.code).toBe("12");
    expect(options.body.zone_id).toBe(ZONE_ID);
    expect(options.body.category_id).toBe(CATEGORY_ID);
  });
});

/* ---------------------------------------------------------------------------
 * T4 — CHEGARA: TAHRIR REJIMIDAGI TRI-STATE QULFI TEGILMAYDI
 * ------------------------------------------------------------------------ */

describe("tahrir rejimi (chegara)", () => {
  test("batafsil javob KELMAGUNCHA saqlash tugmasi YOPIQ qoladi", async () => {
    apiFetch.mockImplementation((path: string) => {
      if (path === ZONES_PATH) {
        return Promise.resolve({
          items: [{ id: ZONE_ID, name: ZONE_NAME }],
          next_cursor: null,
        });
      }
      // `GET /stalls/{id}` ATAYIN javob bermaydi: forma urug'lanmagan
      // holatda qoladi va aynan shu holat o'lchanadi.
      if (path === STALL_DETAIL_PATH) return new Promise(() => {});
      return Promise.reject(new Error(`kutilmagan yo'l: ${path}`));
    });

    renderDialog("edit", STALL_ID);
    await screen.findByRole("option", { name: ZONE_NAME });

    /*
     * ⛔ BU QULF BU VAZIFADA OLIB TASHLANMAYDI. Urug'lanmagan forma
     *   `note` ni bo'sh yuborib mavjud izohni JIMGINA o'chirardi.
     *   Yopilish tetigi — 260816-5yz (tri-state).
     */
    expect(screen.getByRole("button", { name: SAVE })).toBeDisabled();
  });
});
