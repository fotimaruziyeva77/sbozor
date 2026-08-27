/**
 * USTANING 5-QADAMI — ⛔ BO'SH HOLAT VA'DA QILGAN YO'L HAQIQATAN BOR.
 *
 * =============================================================================
 * BU FAYLNING MARKAZIY DA'VOSI (TEST-REPORT 2026-08-14, Topilma №2):
 *
 *   RASTALAR QADAMIDA QO'LDA QO'SHISH TUGMASI BO'LISHI SHART.
 *
 *   Qadamning bo'sh holati «…yoki birinchi rastani qo'lda qo'shing»
 *   deydi — lekin qadamda qo'lda qo'shish tugmasi YO'Q edi. Bu nuqson
 *   sinfi TEST-REPORT dagi №4 va №6 bilan bir xil: interfeys VA'DA
 *   beradi, bajarmaydi. Foydalanuvchi buni tizim nosozligi deb emas,
 *   O'Z XATOSI deb o'qiydi — «tugmani topa olmadim» degan xulosa
 *   Excel importga majburlaydi va bir dona rasta uchun ham fayl
 *   yasashga olib boradi.
 *
 *   ⛔ ICHKI NOMUVOFIQLIK BU DA'VONING ASOSI: 6-qadam (Sotuvchilar)
 *      AYNI naqshni to'liq bajaradi — `ImportPanel` + `Button` +
 *      ro'yxat. T4 shu naqshni NAZORAT sifatida o'lchaydi, ya'ni
 *      tuzatish 5-qadamni 6-qadamga TENGLASHTIRADI, yangi naqsh
 *      o'ylab topmaydi.
 * =============================================================================
 *
 * ⚠ T2 — TUGMA EMAS, YO'L o'lchanadi. «Tugma bor» yolg'iz yetarli emas:
 *   u hech nima ochmasa nuqson faqat SHAKLINI o'zgartirardi. Yaratish
 *   rejimining FARQLOVCHISI — toifa maydoni (`stall-dialog.tsx` D-04:
 *   `create` da maydon BOR va MAJBURIY, `edit` da UMUMAN yo'q), shuning
 *   uchun assert aynan unga qo'yiladi.
 *
 * ⚠ T3 — RBAC KO'ZGUSI (`stalls/page.tsx:78-84` qoidasi): huquq yo'q
 *   bo'lsa tugma YASHIRILMAYDI, RENDER QILINMAYDI. Direktor rolida
 *   `market_data_view` bor (sahifa ochiladi), `stall_manage` yo'q.
 *
 * ⛔ NOMA'LUM YO'L UCHUN MOCK `reject` QAYTARADI, `{}` EMAS. Jimgina
 *    bo'sh javob testni yolg'on-yashil qilardi va qaysi yuza
 *    qoplanmaganini YASHIRARDI — 05-15 ning S-D darsi bilan bir sinf.
 *
 * DIQQAT: bosish `fireEvent` bilan — loyihada `user-event` ishlatilmaydi.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { NuqsTestingAdapter } from "nuqs/adapters/testing";
import type { ComponentProps } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

const apiClientMock = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  apiRequest: vi.fn(),
}));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return {
    ...actual,
    apiFetch: apiClientMock.apiFetch,
    apiRequest: apiClientMock.apiRequest,
  };
});

/*
 * `@/i18n/navigation` `next/navigation` ga tayanadi va u vitest ESM
 * yechimida topilmaydi (`wizard-stepper.test.tsx:39-51` bilan AYNI
 * sabab). Mock `Link` ni oddiy `<a>` ga aylantiradi.
 *
 * QAMROVNI TORAYTIRMAYDI: bu faylning da'volari 5-qadamdagi TUGMA va
 * u ochadigan DIALOG haqida; locale prefiksini qo'yish `next-intl`
 * ning o'z zimmasida va bu yerda sinalmaydi.
 */
vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href, ...rest }: ComponentProps<"a">) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

import messages from "../../../../../../messages/uz-Latn.json";
import MarketSetupPage from "./page";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const TIME_ZONE = "Asia/Tashkent";

/** uz-Latn kataloglaridagi AYNAN qiymatlar. */
const STALL_CREATE = messages.stalls.create;
const STALL_CATEGORY_LABEL = messages.stalls.categoryLabel;
const VENDOR_CREATE = messages.vendors.create;
const STEP_5_LABEL = messages.wizard.step["5"];

/* --- Mock javoblar --------------------------------------------------------- */

const SETUP_STATUS = {
  zones: 2,
  categories: 3,
  tariffs_covered: 3,
  categories_total: 3,
  stalls: 0,
  stalls_with_category: 0,
  vendors: 0,
  calendar_configured: false,
  cameras: 0,
  can_activate: false,
  blocking: [],
};

const ZONES = {
  items: [
    {
      id: "aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa",
      name: "Sabzavot qatori",
      stall_count: 0,
    },
  ],
};

const CATEGORIES = {
  items: [
    {
      id: "bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb",
      name: "Sabzavot",
      stall_count: 0,
    },
  ],
};

const EMPTY_PAGE = { items: [], next_cursor: null };

/**
 * Yo'lga qarab javob beradi — noma'lum yo'l TESTNI YIQITADI.
 *
 * Zona va toifa ro'yxatlari qo'shimcha maydonlarga ega bo'lishi mumkin,
 * lekin `apiFetch` mock qilingani uchun sxema qo'llanmaydi: bu yerda
 * faqat KOMPONENT o'qiydigan maydonlar muhim.
 */
function routeFetch(): void {
  apiClientMock.apiFetch.mockImplementation((path: string) => {
    if (path.startsWith("/markets/") && path.endsWith("/setup-status")) {
      return Promise.resolve(SETUP_STATUS);
    }
    if (path.startsWith("/zones")) return Promise.resolve(ZONES);
    if (path.startsWith("/categories")) return Promise.resolve(CATEGORIES);
    if (path.startsWith("/stalls")) return Promise.resolve(EMPTY_PAGE);
    if (path.startsWith("/vendors")) return Promise.resolve(EMPTY_PAGE);
    return Promise.reject(
      new Error(`Mock qoplamagan yo'l — testning ko'r nuqtasi: ${path}`),
    );
  });
}

function seedSession(roles: readonly string[]): void {
  setSession({
    accessToken: "test-access-token",
    principal: {
      userId: "33333333-3333-4333-8333-333333333333",
      phone: "+998900000000",
      fullName: "Test Admin",
      roles: [...roles],
      marketId: MARKET_ID,
      marketName: "Karmana markaziy bozori",
      isPlatformAdmin: false,
      locale: "uz-Latn",
      mustChangePassword: false,
    },
    markets: [],
  });
}

function renderPage(searchParams: string) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      timeZone={TIME_ZONE}
    >
      <NuqsTestingAdapter searchParams={searchParams}>
        <QueryClientProvider client={client}>
          <AuthProvider>
            <MarketSetupPage />
          </AuthProvider>
        </QueryClientProvider>
      </NuqsTestingAdapter>
    </NextIntlClientProvider>,
  );
}

/** Qobiq `setup-status` kelgunicha skelet chizadi — qadam mazmunini kutamiz. */
async function renderStep(step: number, roles: readonly string[]) {
  seedSession(roles);
  routeFetch();
  const result = renderPage(`?step=${step}`);
  await waitFor(() => {
    expect(apiClientMock.apiFetch).toHaveBeenCalled();
  });
  return result;
}

beforeEach(() => {
  vi.resetAllMocks();
  clearSession();
});

afterEach(() => {
  clearSession();
});

/* ---------------------------------------------------------------------------
 * ⛔ T1 — QO'LDA QO'SHISH YO'LI MAVJUD
 * ------------------------------------------------------------------------ */

describe("5-qadam: qo'lda rasta qo'shish", () => {
  test("⛔ `stalls.create` yorlig'idagi tugma EKRANDA bor", async () => {
    await renderStep(5, ["market_admin"]);

    // Qadam haqiqatan 5-qadam ekanini avval tasdiqlaymiz: `?step`
    // diapazondan chiqib ketsa `fallbackStep()` boshqa qadamni
    // chizardi va test butunlay boshqa ekranni o'lchardi.
    expect(await screen.findByText(STEP_5_LABEL)).toBeInTheDocument();

    expect(
      await screen.findByRole("button", { name: STALL_CREATE }),
    ).toBeInTheDocument();
  });

  test("⛔ tugma YARATISH dialogini ochadi — toifa maydoni bilan (D-04)", async () => {
    await renderStep(5, ["market_admin"]);

    fireEvent.click(await screen.findByRole("button", { name: STALL_CREATE }));

    const dialog = await screen.findByRole("dialog");

    /*
     * TOIFA MAYDONI — yaratish rejimining AYNAN farqlovchisi
     * (`stall-dialog.tsx` D-04: `edit` da bu maydon UMUMAN yo'q).
     * Sarlavha bo'yicha tekshirish yetarli emasdi: u tugma yorlig'i
     * bilan bir xil kalitdan keladi.
     */
    expect(
      await within(dialog).findByLabelText(STALL_CATEGORY_LABEL),
    ).toBeInTheDocument();
  });
});

/* ---------------------------------------------------------------------------
 * ⛔ T3 — RBAC KO'ZGUSI: HUQUQSIZ ROLDA TUGMA UMUMAN YO'Q
 * ------------------------------------------------------------------------ */

describe("`stall_manage` ko'zgusi", () => {
  test("⛔ huquq yo'q rolda tugma RENDER QILINMAYDI", async () => {
    // Direktorda `market_data_view` BOR (sahifa ochiladi), `stall_manage`
    // esa YO'Q — ya'ni bu «sahifa yopiq» emas, «amal yopiq» holati.
    await renderStep(5, ["director"]);

    expect(await screen.findByText(STEP_5_LABEL)).toBeInTheDocument();

    // Rol bo'yicha ham, MATN bo'yicha ham: `aria-disabled` tugma rol
    // qidiruvidan o'tib ketardi.
    expect(screen.queryByRole("button", { name: STALL_CREATE })).toBeNull();
    expect(document.body.textContent).not.toContain(STALL_CREATE);
  });
});

/* ---------------------------------------------------------------------------
 * T4 — NAZORAT: 6-QADAM NAQSHI BUZILMAGAN
 * ------------------------------------------------------------------------ */

describe("6-qadam (nazorat)", () => {
  test("sotuvchi qo'shish tugmasi hamon o'z joyida", async () => {
    await renderStep(6, ["market_admin"]);

    expect(
      await screen.findByRole("button", { name: VENDOR_CREATE }),
    ).toBeInTheDocument();
  });
});
