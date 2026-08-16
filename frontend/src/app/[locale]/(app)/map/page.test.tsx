/**
 * =============================================================================
 * PLAN-XARITA SAHIFASI — ⛔ BOSISHNING **SAHIFA DARAJASIDAGI** DARVOZASI.
 *
 * -----------------------------------------------------------------------
 * ⛔ NEGA `stall-map.test.tsx` YETARLI EMAS (Topilma №C ning ildizi)
 * -----------------------------------------------------------------------
 * O'sha fayl «katak bosilganda karta ochiladi» da'vosini ALLAQACHON
 * o'lchaydi — lekin u O'Z `Harness()` ini yig'adi: `StallMap` va
 * `StallCardDialog` ni qo'lda yonma-yon qo'yadi va tanlangan ID ni o'zi
 * boshqaradi. Ya'ni u KOMPONENTLARNI o'lchaydi, ULARNING ULANISHINI emas.
 *
 * Bu `cameras/page.test.tsx` (Topilma №J) da AYNAN bir marta o'lchangan
 * sinf: qoida bor edi, prop uzatilmagan edi va prop bo'yicha o'lchov
 * nosozlikni HECH QACHON ko'rmasdi. Shuning uchun bu yerda mock
 * qilinadigan yagona narsa — TARMOQ (`apiFetch`). `MapPage` ning O'ZI,
 * `Suspense` chegarasi, `nuqs` adapteri, `useState` lift'i va
 * `hasPermission` HAQIQIY.
 *
 * -----------------------------------------------------------------------
 * ⛔ SHOX (b) — SERVER TOMONI (`GET /stalls/{id}` ning ROL MATRITSASI)
 * -----------------------------------------------------------------------
 * Karta ma'lumotni `GET /stalls/{id}` dan oladi va u `MARKET_DATA_VIEW`
 * USTIGA `VENDOR_VIEW` ni ham talab qiladi (D-09). Bu yerda tarmoq
 * mock qilingani uchun o'sha shox O'LCHANMAYDI — u
 * `tests/integration/test_stall_registry.py` ning zimmasida qoladi va
 * bu chegara ATAYIN yozilgan: klient darvozasi server huquqini
 * o'lchayapman deb da'vo QILMASLIGI kerak.
 * =============================================================================
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ComponentProps } from "react";
import { NextIntlClientProvider } from "next-intl";
import { NuqsTestingAdapter } from "nuqs/adapters/testing";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

/*
 * ⛔ `@/i18n/navigation` MOCK'I — `StallCardDialog` -> `EvidenceLink`
 *    zanjiri tufayli. Sabab `stall-map.test.tsx` da yozilgan (o'sha
 *    zanjir vitest ESM ostida yechilmaydi va fayl «0 test» bo'lardi).
 */
vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href, ...rest }: ComponentProps<"a">) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
  useRouter: () => ({ replace: vi.fn() }),
  usePathname: () => "/map",
}));

const apiClientMock = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiClientMock.apiFetch };
});

import messages from "../../../../../messages/uz-Latn.json";
import MapPage from "./page";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";
import { MAP_DAY_PATH } from "@/lib/map-day-queries";

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const ZONE_ID = "22222222-2222-4222-8222-222222222222";
const STALL_ID = "33333333-3333-4333-8333-333333333333";
const STALL_CODE = "42";
const TIME_ZONE = "Asia/Tashkent";
const NOW = new Date("2026-08-16T09:00:00Z");

const MAP_PATH = "/stalls/map";
const AMOUNT_SOUM = 15_000;

const STALL_DETAIL = {
  id: STALL_ID,
  code: STALL_CODE,
  zone_id: ZONE_ID,
  zone_name: "A zonasi",
  category_id: null,
  category_name: "Sabzavot",
  status: "active",
  vendor_id: null,
  vendor_name: "Karimov A.",
  tariff_soum: AMOUNT_SOUM,
  created_at: "2026-08-01T00:00:00Z",
  phone: null,
  assignment_from: "2026-07-01",
  note: null,
};

const DAY_STATUS = {
  service_date: "2026-08-16",
  market_active: true,
  market_open: true,
  rows: [
    {
      stall_id: STALL_ID,
      state: "due",
      amount_soum: AMOUNT_SOUM,
      unavailable_reason: null,
      paid_soum: 0,
      remaining_soum: AMOUNT_SOUM,
      open_case_id: null,
      open_case_service_date: null,
    },
  ],
};

/**
 * ⛔ MOCK YO'L BO'YICHA MARSHRUTLANADI va NOMA'LUM YO'L RAD ETILADI:
 * `undefined` qaytaruvchi mock sxema validatsiyasida tushunarsiz xato
 * berib, yo'l xatosini yashirardi (`cameras/page.test.tsx` qoidasi).
 */
function routeFetch(): void {
  apiClientMock.apiFetch.mockImplementation((path: string) => {
    if (path === MAP_PATH) {
      return Promise.resolve({
        zones: [
          {
            id: ZONE_ID,
            name: "A zonasi",
            cells: [
              {
                id: STALL_ID,
                code: STALL_CODE,
                status: "active",
                has_vendor: true,
              },
            ],
          },
        ],
      });
    }
    if (path === MAP_DAY_PATH) return Promise.resolve(DAY_STATUS);
    if (path === `/stalls/${STALL_ID}`) return Promise.resolve(STALL_DETAIL);
    return Promise.reject(new Error(`kutilmagan so'rov: ${path}`));
  });
}

let client: QueryClient;

/**
 * ⛔ SAHIFA `layout` DA NIMA BILAN O'RALGAN BO'LSA, TESTDA HAM O'SHA.
 *
 * `NuqsTestingAdapter` MAJBURIY: `MapWorkspace` `useQueryStates` bilan
 * URL holatini o'qiydi va adaptersiz u ish vaqtida yiqilardi — ya'ni
 * nosozlik sahifada emas, testda ko'rinardi va sabab yashirinardi.
 */
function renderPage(roles: readonly string[]) {
  setSession({
    accessToken: "test-access-token",
    markets: [],
    principal: {
      userId: "44444444-4444-4444-8444-444444444444",
      phone: "+998900000000",
      fullName: "Test Admin",
      roles,
      marketId: MARKET_ID,
      marketName: "Karmana markaziy bozori",
      isPlatformAdmin: false,
      locale: "uz-Latn",
      mustChangePassword: false,
    },
  });

  return render(
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      now={NOW}
      timeZone={TIME_ZONE}
    >
      <NuqsTestingAdapter searchParams="">
        <QueryClientProvider client={client}>
          <AuthProvider>
            <MapPage />
          </AuthProvider>
        </QueryClientProvider>
      </NuqsTestingAdapter>
    </NextIntlClientProvider>,
  );
}

function cellButton(): HTMLButtonElement {
  const button = document.querySelector<HTMLButtonElement>(
    `[data-stall-code="${STALL_CODE}"]`,
  );
  if (button === null) throw new Error(`${STALL_CODE} katagi topilmadi`);
  return button;
}

beforeEach(() => {
  vi.resetAllMocks();
  client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
});

afterEach(() => {
  client.clear();
  clearSession();
});

test("HAQIQIY sahifada katak bosilganda rasta kartasi OCHILADI", async () => {
  routeFetch();
  renderPage(["market_admin"]);

  await waitFor(() => expect(cellButton()).toBeInTheDocument());

  fireEvent.click(cellButton());

  const dialog = await screen.findByRole("dialog");
  await waitFor(() => expect(dialog.textContent).toContain("Karimov A."));
  expect(dialog.textContent).toContain(STALL_CODE);
});

test("karta yopilganda dialog DOM'dan chiqadi", async () => {
  /*
   * ⚠ Ochilish YOLG'IZ o'zi yetarli emas: `stallId` sahifa holatida
   *   yashaydi (Pitfall 8) va uni NOLGA qaytarish ULANISHNING ikkinchi
   *   yarmi. Yopilmagan dialog xaritani butunlay bloklab qo'yardi.
   */
  routeFetch();
  renderPage(["market_admin"]);

  await waitFor(() => expect(cellButton()).toBeInTheDocument());
  fireEvent.click(cellButton());
  await screen.findByRole("dialog");

  fireEvent.keyDown(document.activeElement ?? document.body, { key: "Escape" });

  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
});

test("`market_data_view` YO'Q rolda sahifa rad javobini beradi va SO'ROV KETMAYDI", async () => {
  /*
   * ⛔ HUQUQ TEKSHIRUVI SO'ROVDAN OLDIN (`page.tsx:47-49`). Faqat matnni
   *   tekshirish bu kontraktni o'lchamasdi — sahifa rad javobini
   *   ko'rsatib turib, fonda so'rov yuborayotgan bo'lishi mumkin edi.
   */
  routeFetch();
  renderPage(["inspector"]);

  await waitFor(() =>
    expect(document.body.textContent).toContain(messages.errors.forbidden),
  );

  expect(apiClientMock.apiFetch).not.toHaveBeenCalled();
});
