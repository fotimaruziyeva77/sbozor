/**
 * `app-shell.tsx` navigatsiya yozuvi — CR-03 ning IKKINCHI to'sig'i (02-18).
 *
 * NEGA AYNAN SHU FAYL: 02-VERIFICATION.md bo'yicha `NAV_ITEMS` da
 * `/markets/new` yozuvi HECH BIR rol uchun yo'q edi. Ya'ni marshrut ochilgan
 * taqdirda ham (`layout.test.tsx`) usta TOPILMAYDIGAN bo'lib qolardi va
 * foydalanuvchi URL'ni qo'lda terishi kerak edi — bu mahsulot emas.
 *
 * Test qulflaydigan xulq:
 *   1. `market_manage` huquqli rol menyuda «Yangi bozor» havolasini KO'RADI.
 *   2. NAZORAT: `market_manage` YO'Q rol (`market_admin`) uni KO'RMAYDI,
 *      lekin qolgan bo'limlarni ko'radi (ya'ni qobiq yiqilgani uchun emas).
 *   3. UI-SPEC §12.3: mobil pastki panelda ENG KO'PI 5 element (4 + «Ko'proq»)
 *      qoladi va yangi yozuv u yerga TUSHMAYDI — u `system` guruhida.
 *   4. UI-SPEC §12.3: yon panelda yozuv aynan «Tizim» guruhida turadi.
 *
 * DIQQAT: `permission` XAVFSIZLIK CHEGARASI EMAS (`app-shell.tsx:43-47`) —
 * u faqat menyuni yashiradi. 2-testning ma'nosi "ruxsat berilmadi" emas,
 * "shovqin ko'rsatilmadi". Haqiqiy darvoza `markets/new/page.tsx` da va
 * serverda (`POST /markets`, 02-11).
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ComponentProps } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import { AppShell } from "@/components/shell/app-shell";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

/*
 * `@/i18n/navigation` Next.js router kontekstiga tayanadi va u jsdom'da yo'q
 * (`wizard-stepper.test.tsx:40-49` bilan AYNI sabab). Mock `Link` ni oddiy
 * `<a>` ga aylantiradi; locale prefiksini qo'yish `next-intl` ning o'z
 * zimmasida va bu yerda sinalmaydi.
 */
const navigationMock = vi.hoisted(() => ({
  replace: vi.fn(),
  pathname: "/dashboard",
}));

vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href, ...rest }: ComponentProps<"a">) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
  useRouter: () => ({ replace: navigationMock.replace }),
  usePathname: () => navigationMock.pathname,
}));

/** `nav.newMarket` — uz-Latn qiymati (test AYNAN shu katalogni yuklaydi). */
const NEW_MARKET_LABEL = "Yangi bozor";
const NEW_MARKET_HREF = "/markets/new";
/** `nav.groupSystem` — yon paneldagi «Tizim» sarlavhasi. */
const SYSTEM_GROUP_LABEL = "Tizim";
/** `nav.stalls` — 2-testdagi "qobiq baribir chizildi" nazorati. */
const STALLS_LABEL = "Rastalar";

/**
 * UI-SPEC §12.3 KONTRAKTI, `MOBILE_PRIMARY_COUNT` ning nusxasi EMAS.
 *
 * Ataylab modul konstantasidan import qilinmaydi: import qilinsa test
 * implementatsiyani o'ziga o'zi tasdiqlatardi (konstanta 8 ga o'zgarsa test
 * ham 8 ni kutib, jimgina yashil qolardi). Bu yerda 360px kenglikdagi
 * barmoq nishoni (WCAG 2.5.8) talab qiladigan SON qattiq yozilgan.
 */
const MOBILE_MAX_PRIMARY = 4;

function seedRoles(roles: readonly string[]): void {
  setSession({
    accessToken: "test-access-token",
    principal: {
      userId: "33333333-3333-4333-8333-333333333333",
      phone: "+998901234567",
      fullName: "Test Foydalanuvchi",
      roles,
      marketId: "11111111-1111-4111-8111-111111111111",
      marketName: "Karmana markaziy bozori",
      isPlatformAdmin: roles.includes("platform_admin"),
      locale: "uz-Latn",
      mustChangePassword: false,
    },
    markets: [],
  });
}

function renderShell(): void {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  render(
    <NextIntlClientProvider locale="uz-Latn" messages={messages}>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <AppShell>
            <p>sahifa-kontenti</p>
          </AppShell>
        </AuthProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>,
  );
}

/**
 * Mobil pastki panel.
 *
 * IKKALA `<nav>` ning ham `aria-label` i BIR XIL (`shell.sections`), shuning
 * uchun ular yorliq bilan ajratilmaydi. Ajratuvchi belgi — «Ko'proq»
 * TUGMASI: u faqat pastki panelda bor (yon panelda tugma umuman yo'q).
 * Indeks bo'yicha tanlash (`[1]`) markup tartibi o'zgarganda jimgina
 * noto'g'ri panelni tekshirib qo'yardi.
 */
function mobileBar(): HTMLElement {
  const bars = screen.getAllByRole("navigation");
  const bar = bars.find(
    (nav) => within(nav).queryAllByRole("button").length > 0,
  );
  expect(bar, "mobil pastki panel topilmadi").toBeDefined();
  return bar as HTMLElement;
}

beforeEach(() => {
  clearSession();
  vi.resetAllMocks();
  navigationMock.pathname = "/dashboard";
});

afterEach(() => {
  clearSession();
});

describe("AppShell — «Yangi bozor» navigatsiya yozuvi (CR-03)", () => {
  test("`market_manage` huquqli rol menyuda «Yangi bozor» havolasini ko'radi", () => {
    seedRoles(["platform_admin"]);
    renderShell();

    const link = screen.getByRole("link", { name: NEW_MARKET_LABEL });
    expect(link).toHaveAttribute("href", NEW_MARKET_HREF);
  });

  test("NAZORAT: `market_manage` YO'Q rolda havola KO'RINMAYDI", () => {
    // `market_admin` da `stall_manage`/`tariff_manage`/`vendor_manage` BOR,
    // lekin `market_manage` YO'Q (D-07) — bozor YARATISH platforma
    // adminining ishi.
    seedRoles(["market_admin"]);
    renderShell();

    expect(
      screen.queryByRole("link", { name: NEW_MARKET_LABEL }),
    ).not.toBeInTheDocument();

    /*
     * NAZORAT MAJBURIY: usiz bu test qobiq UMUMAN chizilmagan (masalan
     * render yiqilgan) holatda ham yashil ko'rinardi.
     */
    expect(
      screen.getAllByRole("link", { name: STALLS_LABEL }).length,
    ).toBeGreaterThan(0);
  });

  test("UI-SPEC §12.3: mobil panelda eng ko'pi 4 havola va yangi yozuv u yerda EMAS", () => {
    seedRoles(["platform_admin"]);
    renderShell();

    const bar = mobileBar();
    const directLinks = within(bar).getAllByRole("link");

    // 4 havola + «Ko'proq» tugmasi = 5 element (360px'da har biri ≥44px).
    expect(directLinks.length).toBeLessThanOrEqual(MOBILE_MAX_PRIMARY);
    expect(within(bar).getAllByRole("button")).toHaveLength(1);

    /*
     * Yangi yozuv `NAV_ITEMS` ning OXIRIDA va `system` guruhida — ya'ni u
     * «Ko'proq» varag'iga tushadi. Agar u ro'yxat boshiga ko'chirilsa,
     * pastki paneldan eng ko'p ishlatiladigan bo'lim siqib chiqarilardi.
     */
    expect(
      within(bar).queryByRole("link", { name: NEW_MARKET_LABEL }),
    ).not.toBeInTheDocument();
  });

  test("UI-SPEC §12.3: yon panelda yozuv «Tizim» guruhida turadi", () => {
    seedRoles(["platform_admin"]);
    renderShell();

    // Guruh sarlavhasi va uning havolalari bitta konteynerda (`app-shell.tsx`
    // dagi `NAV_GROUPS` render tarmog'i).
    const groupHeading = screen.getByText(SYSTEM_GROUP_LABEL);
    const group = groupHeading.parentElement;
    expect(group, "«Tizim» guruhi konteyneri topilmadi").not.toBeNull();

    expect(
      within(group as HTMLElement).getByRole("link", {
        name: NEW_MARKET_LABEL,
      }),
    ).toHaveAttribute("href", NEW_MARKET_HREF);
  });
});
