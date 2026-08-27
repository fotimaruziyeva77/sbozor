/**
 * MAVJUD FOYDALANUVCHINING ROLLARINI TAHRIRLASH (Topilma №G).
 *
 * =============================================================================
 * BU FAYLNING MARKAZIY DA'VOSI: TAHRIRLASH YO'LI UMUMAN YO'Q EDI.
 *
 *   Backend'da rol yangilash endpointi yo'q edi (`users.py` da faqat
 *   `POST ""`, `/block`, `/unblock`, `/reset-password`), UI'da esa
 *   menyu bandi. Natijada bozor ma'muriyati «rolni o'zgartirish uchun
 *   hisobni o'chirib qayta yaratish» yo'liga majbur bo'lardi — va u
 *   yo'l foydalanuvchining parolini, sessiyalarini va audit izini
 *   uzib yuborardi.
 *
 * ⚠ DIALOG JORIY ROLLAR BILAN OCHILADI (F3) VA BU SHUNCHAKI QULAYLIK
 *   EMAS. Bo'sh holatda ochilgan dialog «saqlash» bosilganda rollarni
 *   QO'SHMAYDI, ALMASHTIRADI — ya'ni foydalanuvchi bilmagan holda
 *   mavjud rolni o'chirib yuborardi. Shakl «hozirgi holat + tahrir»
 *   bo'lishi SHART.
 *
 * ⚠ F5 — Topilma №4 NING NAQSHI. Rolsiz saqlash JIM NO-OP bo'lmaydi:
 *   so'rov yuborilmaydi VA sabab EKRANDA KO'RINADI. Ikkala yarim ham
 *   kerak — birinchisisiz qoida yo'q, ikkinchisisiz foydalanuvchi
 *   «saqlandi shekilli» deb o'ylaydi.
 *
 * DIQQAT: bosish `fireEvent` bilan — loyihada `user-event` ishlatilmaydi.
 * =============================================================================
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
import { EditRolesDialog } from "@/components/users/edit-roles-dialog";
import type { UserListItem } from "@/lib/api-types";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";
import { roleLabelKey } from "@/lib/rbac";

const { apiFetch } = apiClientMock;

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const TARGET_ID = "44444444-4444-4444-8444-444444444444";

const SAVE = messages.common.save;
const ROLES_REQUIRED = messages.users.rolesRequired;

/** Rol yorlig'i — REYESTRDAN hosila, literal EMAS (`roleLabelKey()` ko'zgusi). */
function roleLabel(role: string): string {
  const key = roleLabelKey(role);
  if (key === null) throw new Error(`roleLabelKey topa olmadi: ${role}`);
  return messages.roles[key];
}

const CASHIER_LABEL = roleLabel("cashier");
const INSPECTOR_LABEL = roleLabel("inspector");

const TARGET: UserListItem = {
  id: TARGET_ID,
  phone: "+998901234567",
  full_name: "Kassir Kassirov",
  roles: ["cashier"],
  is_active: true,
  must_change_password: false,
  locale: "uz-Latn",
  created_at: "2026-08-01T05:00:00Z",
};

function seedSession(): void {
  setSession({
    accessToken: "test-access-token",
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
    markets: [],
  });
}

function renderDialog(user: UserListItem = TARGET): {
  onOpenChange: ReturnType<typeof vi.fn>;
} {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const onOpenChange = vi.fn();

  const tree: ReactElement = (
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      timeZone="Asia/Tashkent"
    >
      <QueryClientProvider client={client}>
        <AuthProvider>
          <EditRolesDialog onOpenChange={onOpenChange} open user={user} />
        </AuthProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>
  );

  render(tree);
  return { onOpenChange };
}

function clickSave(): void {
  fireEvent.click(screen.getByRole("button", { name: SAVE }));
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
 * F3 — JORIY ROLLAR OLDINDAN BELGILANGAN
 * ------------------------------------------------------------------------ */

describe("dialog joriy holat bilan ochiladi", () => {
  test("foydalanuvchining roli BELGILANGAN, qolganlari BO'SH", () => {
    renderDialog();

    expect(screen.getByLabelText(CASHIER_LABEL)).toBeChecked();
    expect(screen.getByLabelText(INSPECTOR_LABEL)).not.toBeChecked();
  });
});

/* ---------------------------------------------------------------------------
 * F4 — SAQLASH AYNAN TANLANGAN TO'PLAMNI YUBORADI
 * ------------------------------------------------------------------------ */

describe("saqlash", () => {
  test("`PATCH /users/{id}/roles` ga AYNAN tanlangan to'plam ketadi", async () => {
    apiFetch.mockResolvedValue(null);

    renderDialog();
    fireEvent.click(screen.getByLabelText(INSPECTOR_LABEL));
    clickSave();

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        `/users/${TARGET_ID}/roles`,
        expect.objectContaining({
          method: "PATCH",
          body: { roles: ["cashier", "inspector"] },
        }),
      );
    });
  });

  test("rolni OLIB TASHLASH ham yuboriladi — to'plam almashtiriladi", async () => {
    apiFetch.mockResolvedValue(null);

    renderDialog({ ...TARGET, roles: ["cashier", "inspector"] });
    fireEvent.click(screen.getByLabelText(CASHIER_LABEL));
    clickSave();

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        `/users/${TARGET_ID}/roles`,
        expect.objectContaining({ body: { roles: ["inspector"] } }),
      );
    });
  });
});

/* ---------------------------------------------------------------------------
 * F5 — ⛔ JIM NO-OP YO'Q (Topilma №4 naqshi)
 * ------------------------------------------------------------------------ */

describe("birorta rol tanlanmagan holda saqlash", () => {
  test("⛔ so'rov YUBORILMAYDI va sabab EKRANDA KO'RINADI", async () => {
    renderDialog();
    // Yagona belgilangan rolni olib tashlaymiz -> to'plam bo'sh qoladi.
    fireEvent.click(screen.getByLabelText(CASHIER_LABEL));
    clickSave();

    expect(await screen.findByText(ROLES_REQUIRED)).toBeInTheDocument();
    expect(apiFetch).not.toHaveBeenCalled();
  });

  test("xatoni TUZATGANDA xabar YO'QOLADI (0 -> 1 o'tishi)", async () => {
    /*
     * ⚠ `create-user-dialog` da o'lchangan T2 nuqsonining aynan nusxasi:
     *   qayta validatsiya `selectedRoles.length > 0` ga bog'langanda 0->1
     *   o'tishi QAMRALMAYDI va «tuzatdim, lekin hech nima o'zgarmadi»
     *   holati tug'iladi. Shart `isSubmitted` bo'lishi SHART.
     */
    renderDialog();
    fireEvent.click(screen.getByLabelText(CASHIER_LABEL));
    clickSave();
    await screen.findByText(ROLES_REQUIRED);

    fireEvent.click(screen.getByLabelText(INSPECTOR_LABEL));

    await waitFor(() => {
      expect(screen.queryByText(ROLES_REQUIRED)).toBeNull();
    });
  });
});

/* ---------------------------------------------------------------------------
 * SERVER RAD ETISHI — XOM KOD EMAS, TARJIMA
 * ------------------------------------------------------------------------ */

describe("server rad etganda", () => {
  test("`role_not_allowed` tarjima bilan ko'rsatiladi", async () => {
    const { ApiError } = await import("@/lib/api-client");
    apiFetch.mockRejectedValue(new ApiError(403, "role_not_allowed"));

    renderDialog();
    fireEvent.click(screen.getByLabelText(INSPECTOR_LABEL));
    clickSave();

    expect(
      await screen.findByText(messages.users.roleNotAllowed),
    ).toBeInTheDocument();
  });
});
