/**
 * LoginForm — «sessiya nega tugadi» xabarining darvozasi (260928, D2).
 *
 * =============================================================================
 * NIMA QULFLANADI VA NEGA.
 *
 * O'lchangan holat (260914 auditi): 1987 ta matn ichida «sessiya tugadi»
 * degan bitta ham xabar YO'Q edi. Kassir smena o'rtasida to'satdan kirish
 * sahifasida paydo bo'lardi va sababni hech kim aytmasdi — u uchun bu
 * «dastur buzildi, yozgan to'lovlarim ketdimi?» degani.
 *
 * =============================================================================
 * ⛔ TEST UCHTA HOLATNI FARQLAYDI VA AYNAN SHU FARQ QIMMAT.
 *
 * «Xabar chiqadimi?» degan yakka da'vo YETARLI EMAS: uni `return true`
 * ham qanoatlantirardi. Shuning uchun har bir MANFIY holat ham alohida
 * o'lchanadi — ular xabarni noto'g'ri joyda chiqarish sinfini yopadi:
 *
 *   1. Sessiya O'LDI      -> xabar CHIQADI
 *   2. Odam O'ZI chiqdi   -> xabar CHIQMAYDI  (aks holda chiqish tugmasini
 *                            bosgan odamga «muddatingiz tugadi» deyilardi)
 *   3. Birinchi mehmon    -> xabar CHIQMAYDI  (`restoreSession()` refresh
 *                            cookie yo'qligida BARIBIR yiqiladi va AYNAN
 *                            o'sha `clearSession()` yo'lidan o'tadi —
 *                            usiz har bir yangi mehmon xabarni ko'rardi)
 *   4. Yangi login        -> xabar CHIQMAYDI  (sabab `setSession()` da
 *                            tozalanadi, ya'ni u keyingi safar qaytmaydi)
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ComponentProps, ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import { LoginForm } from "@/components/auth/login-form";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

/* `useRouter` jsdom'da yo'q — `market-picker.test.tsx` bilan ayni naqsh. */
const routerMock = vi.hoisted(() => ({ replace: vi.fn(), push: vi.fn() }));

vi.mock("@/i18n/navigation", () => ({
  useRouter: () => routerMock,
  Link: ({ children, href, ...rest }: ComponentProps<"a">) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

const XABAR = messages.auth.sessionExpiredTitle;

/** Tirik sessiya — «o'lim» va «o'zi chiqdi» holatlarining PREKONDITSIYASI. */
function tirikSessiya(): void {
  setSession({
    accessToken: "test-access-token",
    principal: {
      userId: "33333333-3333-4333-8333-333333333333",
      phone: "+998901234567",
      fullName: "Test Kassir",
      roles: ["cashier"],
      marketId: "11111111-1111-4111-8111-111111111111",
      marketName: "Test bozori",
      isPlatformAdmin: false,
      locale: "uz-Latn",
      mustChangePassword: false,
    },
    markets: [],
  });
}

function chiz(): ReactElement {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return (
    <QueryClientProvider client={client}>
      <NextIntlClientProvider locale="uz-Latn" messages={messages}>
        <AuthProvider>
          <LoginForm />
        </AuthProvider>
      </NextIntlClientProvider>
    </QueryClientProvider>
  );
}

describe("LoginForm — sessiya tugash xabari", () => {
  beforeEach(() => {
    // Har test TOZA holatdan boshlanadi: sabab modul darajasidagi
    // o'zgaruvchida yashaydi va testlar orasida oqib o'tishi mumkin.
    setSession({
      accessToken: null,
      principal: null,
      markets: [],
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  test("sessiya O'LGANDA xabar chiqadi", () => {
    tirikSessiya();
    clearSession(); // standart sabab — `expired`

    render(chiz());

    expect(screen.getByText(XABAR)).toBeInTheDocument();
    // ⛔ Izoh matni ham tekshiriladi: kassirning birinchi savoli
    //    «yozganlarim ketdimi?» va javob AYNAN shu jumlada.
    expect(
      screen.getByText(messages.auth.sessionExpiredNote),
    ).toBeInTheDocument();
  });

  test("odam O'ZI chiqqanda xabar CHIQMAYDI", () => {
    tirikSessiya();
    clearSession("signed_out");

    render(chiz());

    expect(screen.queryByText(XABAR)).not.toBeInTheDocument();
  });

  test("birinchi marta kelgan mehmonga xabar CHIQMAYDI", () => {
    // Sessiya UMUMAN bo'lmagan: `restoreSession()` refresh cookie
    // yo'qligida shu yo'ldan o'tadi.
    clearSession();

    render(chiz());

    expect(screen.queryByText(XABAR)).not.toBeInTheDocument();
  });

  test("yangi login sababni TOZALAYDI", () => {
    tirikSessiya();
    clearSession();
    tirikSessiya(); // muvaffaqiyatli kirish

    render(chiz());

    expect(screen.queryByText(XABAR)).not.toBeInTheDocument();
  });
});
