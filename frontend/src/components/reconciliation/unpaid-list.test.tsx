/**
 * ⛔ G-30 (07-UI-SPEC) DOM YARMI + ⛔ G7-3 (07-RESEARCH) DOM YARMI.
 *
 * =============================================================================
 * ⛔⛔ 1. IKKI SINF ⛔ BIRGA RENDER QILINADI — VA BU MUZOKARASIZ.
 *
 * Sahifada ular yonma-yon turadi, ya'ni yig'indi AYNAN ular orasida
 * tug'iladi. Ikkalasini alohida testda render qilish «orasida son
 * yo'q» da'vosini ⛔ MA'NOSIZ qilardi: bo'sh oraliqda son bo'lishi
 * mumkin ham emas edi.
 *
 * ⛔ DA'VO TO'PLAM TENGLIGI BILAN: «`grandTotal` yo'qmi?» tekshiruvi
 *   yonidagi YANGI nomni ko'rmasdi. Bu yerdagi shakl esa ikki blokdan
 *   TASHQARIDAGI HAR QANDAY raqamda qizaradi — nomi qanday bo'lishidan
 *   qat'i nazar.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 2. DALIL — `<Link>`, KADR EMAS (M-7).
 *
 * `getAllByRole("link")` dalilning HAQIQATAN havola ekanini o'lchaydi,
 * `queryAllByRole("img")` esa kadr ⛔ CHIZILMAGANINI. Ikkinchisi
 * `scripts/reconciliation-copy.test.mjs` dagi STATIK skanning DOM
 * jufti: statik skan «yozib bo'lmaydi» deydi, bu esa «chizilmadi» ni
 * o'lchaydi — ular bir-birini ALMASHTIRMAYDI.
 * =============================================================================
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import type { ComponentProps } from "react";
import { NextIntlClientProvider } from "next-intl";
import { beforeEach, describe, expect, test, vi } from "vitest";

vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href, ...rest }: ComponentProps<"a">) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
  useRouter: () => ({ replace: vi.fn() }),
  usePathname: () => "/reconciliation",
}));

const apiClientMock = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiClientMock.apiFetch };
});

import messages from "../../../messages/uz-Latn.json";
import { UnpaidList } from "@/components/reconciliation/unpaid-list";
import { UnregisteredList } from "@/components/reconciliation/unregistered-list";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const DAY = "2026-08-11";
const CASE_A = "22222222-2222-4222-8222-222222222222";
const CASE_B = "22222222-2222-4222-8222-222222222229";
const VENDOR_ID = "33333333-3333-4333-8333-333333333333";
const SNAPSHOT_ID = "44444444-4444-4444-8444-444444444444";

const UNPAID_ROW = {
  subject_kind: "occupied_unpaid",
  case_id: CASE_A,
  status: "new",
  service_date: DAY,
  stall_code: "14-C",
  vendor_id: VENDOR_ID,
  expected_soum: 30_000,
  paid_soum: 10_000,
  evidence_snapshot_ids: [SNAPSHOT_ID],
};

const UNREGISTERED_ROW = {
  subject_kind: "anomaly",
  case_id: CASE_B,
  status: "in_review",
  service_date: DAY,
  stall_code: "31-A",
  vendor_id: null,
  expected_soum: null,
  paid_soum: null,
  evidence_snapshot_ids: [SNAPSHOT_ID],
};

function routeFetch(roles: string[] = ["director"]) {
  clearSession();
  setSession({
    accessToken: "t",
    markets: [],
    principal: {
      userId: "33333333-3333-4333-8333-333333333333",
      phone: "+998900000000",
      fullName: "Test Direktor",
      roles: roles,
      marketId: MARKET_ID,
      marketName: "Karmana markaziy bozori",
      isPlatformAdmin: false,
      locale: "uz-Latn",
      mustChangePassword: false,
    },
  });

  apiClientMock.apiFetch.mockImplementation((path: string) => {
    if (path.startsWith("/reconciliation/report")) {
      return Promise.resolve({
        day: DAY,
        rows: [UNPAID_ROW, UNREGISTERED_ROW],
        unpaid_count: 1,
        unregistered_count: 1,
        unpaid_expected_soum: 30_000,
      });
    }
    if (path.startsWith("/vendors")) {
      return Promise.resolve({ items: [], next_cursor: null });
    }
    return Promise.reject(new Error(`kutilmagan marshrut: ${path}`));
  });
}

/**
 * ⛔ IKKALA SINF BIRGA — sahifadagi joylashuvning AYNAN nusxasi.
 *
 * O'rovchi `<div>` — bu «ikkala blokdan tashqaridagi hudud», ya'ni
 * yig'indi qatori paydo bo'ladigan YAGONA joy.
 */
async function renderBothClasses() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  const view = render(
    <NextIntlClientProvider locale="uz-Latn" messages={messages} timeZone="Asia/Tashkent">
      <QueryClientProvider client={client}>
        <AuthProvider>
          <div data-testid="workspace">
            <UnpaidList day={DAY} />
            <UnregisteredList day={DAY} />
          </div>
        </AuthProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>,
  );

  await waitFor(() => {
    expect(view.container.querySelector('[aria-busy="true"]')).toBeNull();
  });

  return view;
}

beforeEach(() => {
  vi.resetAllMocks();
  routeFetch();
});

/* -------------------------------------------------------------------------- */
/* G-30 (b) — IKKI SINF ORASIDA SON YO'Q                                      */
/* -------------------------------------------------------------------------- */

describe("⛔ G-30 (b): ikki blokdan TASHQARIDA raqam YO'Q", () => {
  test("⛔ ikkala mazmun ildizidan tashqarida raqamli tugunlar to'plami BO'SH", async () => {
    const { container } = await renderBothClasses();

    const roots = [...container.querySelectorAll("[data-recon-content]")];
    expect(roots.map((node) => node.getAttribute("data-recon-content"))).toEqual([
      "unpaid",
      "unregistered",
    ]);

    /*
     * ⛔ IKKI BLOKNING MATNINI O'ROVCHINING MATNIDAN AYIRAMIZ. Qolgani —
     *   ularning ORASIDAGI matn, ya'ni yig'indi qatori tug'iladigan
     *   yagona joy.
     */
    const workspace = screen.getByTestId("workspace");
    const outside = roots.reduce(
      (text, root) => text.replace(root.textContent ?? "", ""),
      workspace.textContent ?? "",
    );

    const numbersOutside = outside.match(/\d+/gu) ?? [];

    /*
     * ⛔ TO'PLAM TENGLIGI, «`grandTotal` yo'qmi?» EMAS: nomga qadalgan
     *   da'vo yonidagi YANGI nomni ko'rmasdi. Bu shakl esa nomi qanday
     *   bo'lishidan qat'i nazar HAR QANDAY oraliq raqamda qizaradi.
     */
    expect(new Set(numbersOutside)).toEqual(new Set());
  });

  test("⛔ HAR sinf O'Z sanog'ini O'Z bloki ICHIDA beradi", async () => {
    const { container } = await renderBothClasses();

    const unpaid = container.querySelector('[data-recon-content="unpaid"]');
    const unregistered = container.querySelector('[data-recon-content="unregistered"]');

    /* Sinf A — sanoq VA summa (qarz mavjud). */
    expect(unpaid?.textContent).toContain("14-C");
    expect(within(unpaid as HTMLElement).getAllByRole("row").length).toBeGreaterThan(1);

    /* ⛔ Sinf B — FAQAT sanoq. Summa MAVJUD EMAS (tarif bilinmaydi). */
    expect(unregistered?.textContent).toContain("31-A");
    expect(unregistered?.textContent).not.toContain(messages.recon.outstandingColumn);
  });

  test("⛔ sinf B da qarz ustuni YO'Q — nol qo'shilmaydi", async () => {
    const { container } = await renderBothClasses();

    const unregistered = container.querySelector('[data-recon-content="unregistered"]');
    const headers = within(unregistered as HTMLElement)
      .getAllByRole("columnheader")
      .map((node) => node.textContent);

    /*
     * ⛔ USTUNLAR TO'PLAMI TENGLIGI: sotuvchi ustuni bu sinfda BO'LMASLIGI
     *   kerak (biriktirilgan sotuvchi TA'RIFAN yo'q) va summa ustunlari
     *   ham — ularning nol bilan to'ldirilishi KAM KO'RSATILGAN
     *   YO'QOTISHNING boshlanishi bo'lardi.
     */
    expect(new Set(headers)).toEqual(
      new Set([
        messages.recon.stallColumn,
        messages.recon.dayColumn,
        messages.recon.evidenceColumn,
        messages.recon.statusColumn,
      ]),
    );
  });
});

/* -------------------------------------------------------------------------- */
/* G7-3 — DALIL HAVOLA, KADR EMAS                                             */
/* -------------------------------------------------------------------------- */

describe("⛔ G7-3 (07-RESEARCH): dalil DOM'da HAVOLA", () => {
  test("⛔ dalil `<Link>` sifatida chiziladi va `/billing?day=` ga boradi", async () => {
    await renderBothClasses();

    const links = screen.getAllByRole("link", { name: messages.recon.evidenceOpen });

    /* Ikkala sinfda ham bittadan qator — ikkita havola. */
    expect(links).toHaveLength(2);
    for (const link of links) {
      expect(link.getAttribute("href")).toBe(`/billing?day=${DAY}`);
      /* ⛔ Yangi oyna YO'Q: ilovaning yangi nusxasi auth holatini tiklaydi. */
      expect(link.getAttribute("target")).toBeNull();
    }
  });

  test("⛔ birorta kadr CHIZILMAYDI", async () => {
    const { container } = await renderBothClasses();

    /*
     * ⛔ IKKI KANAL: rol bo'yicha VA teg bo'yicha. Rol bo'yicha da'vo
     *   `alt=""` bilan chizilgan kadrni KO'RMASDI (u `presentation`
     *   roliga tushadi), teg bo'yicha da'vo esa CSS fonini ko'rmasdi —
     *   uni statik skan ushlaydi.
     */
    expect(screen.queryAllByRole("img")).toHaveLength(0);
    expect(container.querySelectorAll("img")).toHaveLength(0);
  });

  test("⛔ HUQUQSIZ ko'ruvchida dalil affordansi UMUMAN chizilmaydi", async () => {
    /*
     * ⚠⚠ BU SHOX BUGUNGI MATRITSADA ERISHIB BO'LMAYDI — VA IZOH SHU
     *    SABABDAN TURIBDI.
     *
     * Hisobotni ko'ra oladigan ikkala rolda ham kadr huquqi BOR, ya'ni
     * real sessiyada bu holat UCHRAMAYDI. Rollar esa SUN'IY berilgan.
     *
     * ⛔ TESTNI «FOYDASIZ» DEB O'CHIRMANG: u KELAJAKKA mo'ljallangan
     *   qo'riqchi. Matritsa o'zgargan kunda (masalan hisobot huquqi
     *   kadrsiz rolga berilganda) bu yagona da'vo affordansning
     *   sizib chiqishini ushlaydi. O'chirilgan tugma ham YARAMAYDI —
     *   u MAVJUD imkoniyatni e'lon qilardi.
     */
    routeFetch(["cashier", "market_admin_without_camera"]);

    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    const { container } = render(
      <NextIntlClientProvider locale="uz-Latn" messages={messages} timeZone="Asia/Tashkent">
        <QueryClientProvider client={client}>
          <AuthProvider>
            <UnpaidList day={DAY} />
          </AuthProvider>
        </QueryClientProvider>
      </NextIntlClientProvider>,
    );

    await waitFor(() => {
      expect(container.querySelector('[aria-busy="true"]')).toBeNull();
    });

    /* ⛔ Element UMUMAN yo'q — na havola, na o'chirilgan tugma. */
    expect(screen.queryAllByRole("link")).toHaveLength(0);
    expect(screen.queryByText(messages.recon.evidenceOpen)).toBeNull();

    /* NAZORAT: qator O'ZI chizilgan, ya'ni bo'sh ro'yxat emas. */
    expect(container.textContent).toContain("14-C");
  });

  test("⛔ DALILSIZ qatorda ham affordans chizilmaydi (05-14 darsi)", async () => {
    apiClientMock.apiFetch.mockImplementation((path: string) => {
      if (path.startsWith("/reconciliation/report")) {
        return Promise.resolve({
          day: DAY,
          rows: [{ ...UNPAID_ROW, evidence_snapshot_ids: [] }],
          unpaid_count: 1,
          unregistered_count: 0,
          unpaid_expected_soum: 30_000,
        });
      }
      return Promise.resolve({ items: [], next_cursor: null });
    });

    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    const { container } = render(
      <NextIntlClientProvider locale="uz-Latn" messages={messages} timeZone="Asia/Tashkent">
        <QueryClientProvider client={client}>
          <AuthProvider>
            <UnpaidList day={DAY} />
          </AuthProvider>
        </QueryClientProvider>
      </NextIntlClientProvider>,
    );

    await waitFor(() => {
      expect(container.querySelector('[aria-busy="true"]')).toBeNull();
    });

    /* ⛔ Marshrut bermagan qator uchun platsholder ham qo'yilmaydi. */
    expect(screen.queryAllByRole("link")).toHaveLength(0);
    expect(container.textContent).toContain("14-C");
  });
});
