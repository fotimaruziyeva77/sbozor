/**
 * FOYDALANUVCHILAR RO'YXATI — AMALLAR MENYUSINING ROL BANDI (Topilma №G).
 *
 * =============================================================================
 * ⛔ BU FAYL DIALOGNI EMAS, MENYUNI O'LCHAYDI.
 *
 *   `edit-roles-dialog.test.tsx` dialogning O'ZINI (joriy rollar, yuborilgan
 *   to'plam, bo'sh to'plam) o'lchaydi. Topilma №G ning ikkinchi yarmi esa
 *   YO'LNING BORLIGI: dialog qurilib, menyuga band qo'shilmasa,
 *   foydalanuvchi uni HECH QACHON ocha olmasdi.
 *
 * ⚠ F2 — «O'ZINING QATORIDA BAND YO'Q» VA U «BLOKLASH» DAN AJRATILADI.
 *   Ikkalasi ham serverda rad etiladi (400), lekin UI ularga BOSHQACHA
 *   munosabatda bo'ladi va farq ataylab:
 *
 *     * «Bloklash» — bandning muvaffaqiyat yo'li BOR (boshqa qatorda),
 *       o'z qatorida esa server sababni AYTADI. Uni yashirish
 *       foydalanuvchiga «bu amal umuman yo'q» degan yolg'on berardi.
 *     * «Rollarni tahrirlash» — o'z qatorida uning HECH QANDAY
 *       muvaffaqiyat yo'li yo'q, ya'ni u o'lik affordans bo'lardi
 *       (Topilma №F bilan aynan bir xil sinf).
 *
 * ⚠ UCHINCHI DA'VO — 3-DARVOZANING KO'ZGUSI. Bozor admini `market_admin`
 *   rolli hisobning bandini KO'RMAYDI: server uni 403 bilan rad etadi va
 *   ko'rsatib turish yana o'lik affordans bo'lardi. Bu server
 *   darvozasining TAKRORI EMAS — haqiqiy qaror hamon 403.
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
import { UserList } from "@/components/users/user-list";
import type { UserListItem } from "@/lib/api-types";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const { apiFetch } = apiClientMock;

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const SELF_ID = "33333333-3333-4333-8333-333333333333";
const CASHIER_ID = "44444444-4444-4444-8444-444444444444";
const ADMIN_ID = "55555555-5555-4555-8555-555555555555";

const EDIT_ROLES = messages.users.editRoles;
const BLOCK = messages.users.block;

function member(
  id: string,
  roles: readonly string[],
  fullName: string,
): UserListItem {
  return {
    id,
    phone: `+99890000${id.slice(0, 4)}`,
    full_name: fullName,
    roles: [...roles],
    is_active: true,
    must_change_password: false,
    locale: "uz-Latn",
    created_at: "2026-08-01T05:00:00Z",
  };
}

const SELF = member(SELF_ID, ["market_admin"], "Men O'zim");
const CASHIER = member(CASHIER_ID, ["cashier"], "Kassir Kassirov");
const OTHER_ADMIN = member(ADMIN_ID, ["market_admin"], "Ikkinchi Admin");

function seedSession(roles: readonly string[] = ["market_admin"]): void {
  setSession({
    accessToken: "test-access-token",
    principal: {
      userId: SELF_ID,
      phone: "+998900000000",
      fullName: "Men O'zim",
      roles,
      marketId: MARKET_ID,
      marketName: "Karmana markaziy bozori",
      isPlatformAdmin: false,
      locale: "uz-Latn",
      mustChangePassword: false,
    },
    markets: [],
  });
}

function renderList(items: readonly UserListItem[]): void {
  apiFetch.mockImplementation((path: string) => {
    if (path === "/users") return Promise.resolve({ items });
    return Promise.reject(new Error(`kutilmagan so'rov: ${path}`));
  });

  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  const tree: ReactElement = (
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      timeZone="Asia/Tashkent"
    >
      <QueryClientProvider client={client}>
        <AuthProvider>
          <UserList onTemporaryPassword={vi.fn()} />
        </AuthProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>
  );

  render(tree);
}

/** Berilgan a'zoning amallar menyusini ochadi. */
async function openActions(user: UserListItem): Promise<void> {
  const trigger = await screen.findByRole("button", {
    name: `${messages.users.actions}: ${user.full_name}`,
  });
  fireEvent.click(trigger);
  fireEvent.keyDown(trigger, { key: "Enter" });
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
 * F1 — BOSHQA FOYDALANUVCHI: BAND BOR
 * ------------------------------------------------------------------------ */

describe("`user_manage` huquqli sessiya", () => {
  test("boshqa a'zoning menyusida «Rollarni tahrirlash» BOR", async () => {
    renderList([SELF, CASHIER]);
    await openActions(CASHIER);

    await waitFor(() => {
      expect(screen.getByText(EDIT_ROLES)).toBeInTheDocument();
    });
  });
});

/* ---------------------------------------------------------------------------
 * F2 — O'Z QATORI: ROL BANDI YO'Q, «BLOKLASH» ESA JOYIDA
 * ------------------------------------------------------------------------ */

describe("o'z qatori", () => {
  test("rol bandi YO'Q, lekin «Bloklash» QOLADI", async () => {
    renderList([SELF, CASHIER]);
    await openActions(SELF);

    await waitFor(() => {
      expect(screen.getByText(BLOCK)).toBeInTheDocument();
    });
    expect(screen.queryByText(EDIT_ROLES)).toBeNull();
  });
});

/* ---------------------------------------------------------------------------
 * 3-DARVOZANING KO'ZGUSI — TENG ADMIN
 * ------------------------------------------------------------------------ */

describe("teng huquqli a'zo", () => {
  test("bozor admini boshqa `market_admin` uchun rol bandini KO'RMAYDI", async () => {
    renderList([SELF, OTHER_ADMIN]);
    await openActions(OTHER_ADMIN);

    await waitFor(() => {
      expect(screen.getByText(BLOCK)).toBeInTheDocument();
    });
    expect(screen.queryByText(EDIT_ROLES)).toBeNull();
  });

  test("NAZORAT: platforma admini AYNAN o'sha qatorda bandni KO'RADI", async () => {
    /*
     * Usiz yuqoridagi da'vo «band hech qachon chizilmaydi» holatida ham
     * yashil qolardi — ya'ni ko'zguning DARAJAGA bog'liqligi
     * isbotlanmasdi (backend B5/B6 juftligi bilan aynan bir xil sabab).
     */
    clearSession();
    setSession({
      accessToken: "test-access-token",
      principal: {
        userId: SELF_ID,
        phone: "+998900000000",
        fullName: "Men O'zim",
        roles: ["platform_admin"],
        marketId: MARKET_ID,
        marketName: "Karmana markaziy bozori",
        isPlatformAdmin: true,
        locale: "uz-Latn",
        mustChangePassword: false,
      },
      markets: [],
    });

    renderList([SELF, OTHER_ADMIN]);
    await openActions(OTHER_ADMIN);

    await waitFor(() => {
      expect(screen.getByText(EDIT_ROLES)).toBeInTheDocument();
    });
  });
});
