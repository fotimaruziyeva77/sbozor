/**
 * TARIF DIALOGI — ⛔ BO'SH TOIFA RO'YXATI BOSHI BERK KO'CHA EMAS (F-3).
 *
 * =============================================================================
 * BU FAYLNING MARKAZIY DA'VOSI:
 *
 *   Toifalar ro'yxati BO'SH bo'lganda «Saqlash» tugmasi BOSILADI va
 *   `tariffs.categoryRequired` EKRANGA CHIQADI.
 *
 *   Ilgari tugma `disabled={categories.length === 0 || isSubmitting}` edi
 *   va u `tariffs.noCategories` placeholder'iga ZID turardi: matn «avval
 *   toifa qo'shing» deb NIMA QILISH kerakligini aytardi, tugma esa
 *   bosilmasdi va bosilmaslikning sababi hech qayerda ko'rinmasdi.
 *   Bir signal ikkinchisini bekor qilsa, ishonarlisi — KO'RINADIGANI.
 * =============================================================================
 *
 * ⚠ `min_valid_from` SERVERDAN keladi va bu yerda ham QAYTA HISOBLANMAYDI
 *   (T-02-119a) — prop sifatida beriladi.
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
import { TariffDialog } from "@/components/tariffs/tariff-dialog";
import type { CategoryItem } from "@/lib/api-types";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const { apiFetch } = apiClientMock;

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const CATEGORY_ID = "33333333-3333-4333-8333-333333333333";

const CATEGORY_NAME = "Sabzavotlar";

/** uz-Latn kataloglaridagi AYNAN qiymatlar. */
const SAVE = messages.common.save;
const CATEGORY_REQUIRED = messages.tariffs.categoryRequired;
const AMOUNT_LABEL = messages.tariffs.amountLabel;
const VALID_FROM_LABEL = messages.tariffs.validFromLabel;

/** `Field` ning `${id}-error` konvensiyasi (`ui/field.tsx`). */
const CATEGORY_ERROR_ID = "tariff-category-error";

const TARIFFS_PATH = "/tariffs";

/** Sana o'lchovi qat'iy: «bugun» va serverning eng erta sanasi qadalgan. */
const NOW = new Date("2026-08-16T04:00:00Z");
const MIN_VALID_FROM = "2026-08-20";

const CATEGORIES: readonly CategoryItem[] = [
  {
    id: CATEGORY_ID,
    name: CATEGORY_NAME,
    stall_count: 12,
    current_tariff_soum: null,
  },
];

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

function renderDialog(categories: readonly CategoryItem[]): void {
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
      now={NOW}
      timeZone="Asia/Tashkent"
    >
      <QueryClientProvider client={client}>
        <AuthProvider>
          <TariffDialog
            categories={categories}
            minValidFrom={MIN_VALID_FROM}
            onOpenChange={vi.fn()}
            open
            tariff={null}
          />
        </AuthProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>
  );

  render(tree);
}

function saveButton(): HTMLElement {
  return screen.getByRole("button", { name: SAVE });
}

function createCalls(): unknown[][] {
  return apiFetch.mock.calls.filter(
    (args: unknown[]) => args[0] === TARIFFS_PATH,
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
 * ⛔ T1/T2 — BO'SH RO'YXATDA TUGMA BOSILADI VA SABAB KO'RINADI
 * ------------------------------------------------------------------------ */

describe("toifalar ro'yxati bo'sh", () => {
  test("⛔ «Saqlash» YOPILMAYDI va bosilganda sabab ko'rinadi", async () => {
    renderDialog([]);

    expect(saveButton()).toBeEnabled();

    fireEvent.click(saveButton());

    await waitFor(() => {
      expect(document.getElementById(CATEGORY_ERROR_ID)).not.toBeNull();
    });
    expect(document.getElementById(CATEGORY_ERROR_ID)?.textContent).toBe(
      CATEGORY_REQUIRED,
    );
  });

  test("⛔ `POST /tariffs` YUBORILMAYDI — qulf saqlanadi", async () => {
    renderDialog([]);

    fireEvent.click(saveButton());

    await waitFor(() => {
      expect(document.getElementById(CATEGORY_ERROR_ID)).not.toBeNull();
    });
    expect(createCalls()).toHaveLength(0);
  });
});

/* ---------------------------------------------------------------------------
 * T3 — NAZORAT: TOIFA BO'LGANDA AYNAN BITTA SO'ROV KETADI
 * ------------------------------------------------------------------------ */

describe("toifa mavjud (nazorat)", () => {
  test("AYNAN BITTA `POST /tariffs` ketadi", async () => {
    apiFetch.mockResolvedValue({
      id: "66666666-6666-4666-8666-666666666666",
      category_id: CATEGORY_ID,
      amount_soum: 15000,
      valid_from: MIN_VALID_FROM,
    });

    renderDialog(CATEGORIES);

    fireEvent.change(screen.getByLabelText(AMOUNT_LABEL), {
      target: { value: "15000" },
    });
    fireEvent.change(screen.getByLabelText(VALID_FROM_LABEL), {
      target: { value: MIN_VALID_FROM },
    });
    fireEvent.click(saveButton());

    await waitFor(() => {
      expect(createCalls()).toHaveLength(1);
    });

    const options = createCalls()[0][1] as {
      body: Record<string, unknown>;
      method: string;
    };
    expect(options.method).toBe("POST");
    expect(options.body.category_id).toBe(CATEGORY_ID);
    // Pul BUTUN so'm (spec §6) — satr emas, `number`.
    expect(options.body.amount_soum).toBe(15000);
    expect(options.body.valid_from).toBe(MIN_VALID_FROM);
  });
});
