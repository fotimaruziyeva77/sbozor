/**
 * ⛔ B-6 NING DOM YARMI — «JIM QIRQILGAN NAVBAT» SINFI.
 *
 * =============================================================================
 * ⛔⛔ NEGA BU FAYL BOR: EKRAN YOLG'ON GAPIRMAYDI, U SUKUT SAQLAYDI.
 *
 * Sanoqlar server kontrakti bo'yicha ⛔ KUN BO'YICHA TO'LIQ keladi, jadval
 * esa bir sahifada ⛔ 50 qator. 300–1000 rastali Karmana bozorida direktor
 * «Yangi 120» yozuvini va 50 qatorli jadvalni ⛔ BIR EKRANDA ko'rardi,
 * qolgan 70 tasi esa DOM'da ⛔ UMUMAN YO'Q edi.
 *
 * ⛔ YO'QOLGAN QATOR — YO'QOLGAN SANOQDAN QIMMATROQ: yonidagi son unga
 *    ⛔ ZID gapiradi. Bir-biriga zid ikki raqamni ko'rgan direktor
 *    ekranning ⛔ HAMMASIGA ishonmay qo'yadi (§1.2 ssenariysi) — ya'ni
 *    yetishmayotgan funksiyadan ko'ra QIMMATROQ nuqson.
 *
 * -----------------------------------------------------------------------
 * ⛔ DA'VOLAR MOCK'DAGI AYNAN QIYMATLARDAN HOSILA
 * -----------------------------------------------------------------------
 * Qator SONI mock massivining UZUNLIGIDAN, sanoq esa mock envelope'idagi
 * AYNAN sondan olinadi. «Jadval bormi?» sinfidagi da'vo qatorlarni
 * jimgina tashlab ketadigan filtrni ⛔ KO'RMASDI.
 * =============================================================================
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ComponentProps } from "react";
import { NextIntlClientProvider } from "next-intl";
import { beforeEach, describe, expect, test, vi } from "vitest";

/*
 * `@/i18n/navigation` Next.js router kontekstiga tayanadi va u jsdom'da
 * YO'Q. Tafsilot dialogi (yopiq holatda ham) dalil havolasini import
 * qiladi — mock busiz butun modul daraxti yiqilardi.
 */
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
import { CaseList } from "@/components/reconciliation/case-list";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const DAY = "2026-08-11";

/**
 * ⛔ SERVER SAHIFASINING O'LCHAMI — TESTDA QAYTA YOZILGAN.
 *
 * ⛔ `CASE_PAGE_SIZE` moduldan IMPORT QILINMAYDI: darvoza o'zi
 *    tekshirayotgan qiymatni tekshirilayotgan moduldan olsa, ikkalasi
 *    BIRGA o'zgarganda `limit=` da'vosi JIMGINA yashil qolardi (05-13
 *    darsi, `readTsRegistry()` docstringi bilan ayni sabab).
 */
const PAGE_SIZE = 50;
const SECOND_PAGE_ROWS = 20;

/** Serverning UNUMSIZ kursori — klient uni PARSE QILMAYDI. */
const CURSOR = "2026-08-12T04:25:00+00:00|22222222-2222-4222-8222-222222222299";

/**
 * ⛔ SANOQLAR SAHIFADAN MUSTAQIL (server kontrakti, `reconciliation.py`).
 *
 * Ular HAR sahifada BUTUN kunning soni bo'lib keladi, ya'ni ikkinchi
 * sahifa yuklanganda ⛔ O'ZGARMASLIGI SHART. Yig'ilib ketgan sanoq
 * «Yangi 240» berardi — ya'ni B-6 ni teskari tomondan takrorlardi.
 */
const COUNTS = {
  new_count: 120,
  in_review_count: 7,
  justified_count: 17,
  unjustified_count: 8,
};

/**
 * ⛔ HAR QATOR DOM'DA AJRALIB TURADI — VA BU ATAYIN.
 *
 * `assignee_user_id` ning DASTLABKI 8 belgisi ekranda chiziladi
 * (`case-list.tsx`), ya'ni indeksni O'SHA joyga qo'yish har qatorga
 * ⛔ KO'RINADIGAN identifikator beradi. Busiz barcha qatorlar bir xil
 * HTML berardi va «sahifalar kesishmaydi» da'vosi ⛔ HECH NIMANI
 * o'lchamasdi — takrorlangan qator ham, yo'qolgani ham bir xil ko'rinardi.
 */
function caseRow(index: number) {
  const suffix = String(index).padStart(4, "0");
  return {
    case_id: `22222222-2222-4222-8222-2222222${suffix}`,
    subject_kind: "occupied_unpaid",
    anomaly_id: null,
    charge_id: `33333333-3333-4333-8333-3333333${suffix}`,
    service_date: DAY,
    status: "new",
    assignee_user_id: `${suffix}4444-4444-4444-8444-444444444444`,
    created_at: `${DAY}T04:25:00Z`,
  };
}

const FIRST_PAGE = Array.from({ length: PAGE_SIZE }, (_, i) => caseRow(i));
const SECOND_PAGE = Array.from({ length: SECOND_PAGE_ROWS }, (_, i) =>
  caseRow(PAGE_SIZE + i),
);

function envelope(rows: ReturnType<typeof caseRow>[], nextCursor: string | null) {
  return { day: DAY, rows, ...COUNTS, next_cursor: nextCursor };
}

/** Ikki sahifali server — kursor BOR/YO'Q bo'yicha shox tanlanadi. */
function routeTwoPages() {
  apiClientMock.apiFetch.mockImplementation((path: string) => {
    if (!path.startsWith("/reconciliation/cases")) {
      return Promise.reject(new Error(`kutilmagan marshrut: ${path}`));
    }
    return Promise.resolve(
      path.includes("cursor=")
        ? envelope(SECOND_PAGE, null)
        : envelope(FIRST_PAGE, CURSOR),
    );
  });
}

/** Bitta sahifali server — `next_cursor === null`. */
function routeOnePage() {
  apiClientMock.apiFetch.mockImplementation((path: string) => {
    if (!path.startsWith("/reconciliation/cases")) {
      return Promise.reject(new Error(`kutilmagan marshrut: ${path}`));
    }
    return Promise.resolve(envelope(FIRST_PAGE, null));
  });
}

async function renderList() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  const view = render(
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      timeZone="Asia/Tashkent"
    >
      <QueryClientProvider client={client}>
        <AuthProvider>
          <CaseList day={DAY} />
        </AuthProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>,
  );

  /*
   * ⚠ KUTISH SIGNALI `aria-busy`, formatlangan son EMAS: `Intl` uzilmas
   *   bo'shliq qo'yadi va Testing Library uni normalizatsiya qiladi.
   */
  await waitFor(() => {
    expect(view.container.querySelector('[aria-busy="true"]')).toBeNull();
  });

  return view;
}

function rowCount(container: HTMLElement): number {
  return container.querySelectorAll("tbody tr").length;
}

function loadMoreButton(): HTMLElement | null {
  return screen.queryByRole("button", { name: messages.recon.loadMore });
}

beforeEach(() => {
  vi.resetAllMocks();
  clearSession();
  setSession({
    accessToken: "t",
    markets: [],
    principal: {
      userId: "33333333-3333-4333-8333-333333333333",
      phone: "+998900000000",
      fullName: "Test Direktor",
      roles: ["director"],
      marketId: MARKET_ID,
      marketName: "Karmana markaziy bozori",
      isPlatformAdmin: false,
      locale: "uz-Latn",
      mustChangePassword: false,
    },
  });
  routeTwoPages();
});

/* -------------------------------------------------------------------------- */
/* (1) IKKINCHI SAHIFAGA YO'L BOR                                             */
/* -------------------------------------------------------------------------- */

describe("⛔ B-6 (1): navbat 50 qatorda JIM QIRQILMAYDI", () => {
  test("⛔ birinchi renderda 50 qator + [Yana yuklash]; bosilgandan keyin 70 va tugma YO'Q", async () => {
    const { container } = await renderList();

    expect(rowCount(container)).toBe(PAGE_SIZE);
    expect(loadMoreButton()).not.toBeNull();

    fireEvent.click(loadMoreButton() as HTMLElement);

    await waitFor(() => {
      expect(rowCount(container)).toBe(PAGE_SIZE + SECOND_PAGE_ROWS);
    });

    /*
     * ⛔ TUGMA UMUMAN YO'Q, «o'chirilgan» EMAS: mavjud lekin ishlamaydigan
     *   boshqaruv MAVJUD BO'LMAGAN imkoniyatni e'lon qilardi.
     */
    expect(loadMoreButton()).toBeNull();
    /*
     * ⛔ ANIQ BYUDJET — VA U O'LCHOVDAN CHIQQAN (quick 260816-75e).
     *
     * Bu test IKKI marta render qiladi (50 qator, keyin 70) va YOLG'IZ
     * yugurganda 4504 ms oladi — vitest'ning standart 5000 ms chegarasidan
     * atigi ~10 % pastda. To'plamga ikkita yangi test FAYLI qo'shilgach
     * (76 -> 78) parallel ishchilar orasidagi CPU raqobati uni chegaradan
     * chiqarib yubordi: fayl YOLG'IZ yugurganda 12/12 yashil, to'plam
     * ichida esa AYNAN shu test `Test timed out in 5000ms` beradi.
     *
     * ⚠ BU XULQ REGRESSIYASI EMAS va shuning uchun testning O'ZI
     *   o'zgartirilmadi — faqat byudjeti o'lchovga MOSLANDI. Qiymat
     *   `stall-map.test.tsx` ning 1000 katakli testlaridagi bilan bir xil
     *   konvensiyada (`}, 30_000)`) yoziladi.
     */
  }, 20_000);

  test("⛔ SAHIFALAR KESISHMAYDI — ikkinchi sahifaning identifikatorlari birinchisida YO'Q", async () => {
    const { container } = await renderList();

    fireEvent.click(loadMoreButton() as HTMLElement);
    await waitFor(() => {
      expect(rowCount(container)).toBe(PAGE_SIZE + SECOND_PAGE_ROWS);
    });

    /*
     * ⛔ TAKRORLANGAN QATOR — SILJISH BO'YICHA sahifalashning belgisi
     *   (navbat so'rovlar ORASIDA o'sadi). Keyset kursori uni oldini
     *   oladi va bu da'vo AYNAN o'sha regressiyada qizaradi.
     *
     * ⛔ DA'VO CHIZILGAN MATN USTIDAN, mock massivi ustidan EMAS: massiv
     *   ustidagi tekshiruv o'zining KIRISHINI tasdiqlab, komponent
     *   qatorni ikki marta chizsa ham yashil qolardi.
     */
    const shown = [...container.querySelectorAll("tbody tr")].map(
      (node) => node.querySelectorAll("td")[2]?.textContent ?? "",
    );

    expect(shown).toHaveLength(PAGE_SIZE + SECOND_PAGE_ROWS);
    expect(new Set(shown).size).toBe(shown.length);

    /* Va chizilgan to'plam AYNAN ikki sahifaning birlashmasi. */
    expect(new Set(shown)).toEqual(
      new Set(
        [...FIRST_PAGE, ...SECOND_PAGE].map((row) =>
          row.assignee_user_id.slice(0, 8),
        ),
      ),
    );
  });

  test("⛔ `next_cursor === null` bo'lgan javobda tugma UMUMAN chizilmaydi", async () => {
    routeOnePage();

    const { container } = await renderList();

    expect(rowCount(container)).toBe(PAGE_SIZE);
    expect(loadMoreButton()).toBeNull();

    /* NAZORAT: ro'yxat CHIZILGAN, ya'ni tugma bo'sh sahifadan yo'q emas. */
    expect(container.textContent).toContain(messages.recon.casesTitle);
  });
});

/* -------------------------------------------------------------------------- */
/* (2) SANOQLAR BIRINCHI SAHIFADAN VA O'ZGARMAYDI                             */
/* -------------------------------------------------------------------------- */

describe("⛔ B-6 (2): sanoq SAHIFADAN MUSTAQIL", () => {
  test("⛔ to'rt sanoq ikkinchi sahifadan KEYIN ham O'ZGARMAYDI", async () => {
    const { container } = await renderList();

    const dl = container.querySelector("dl") as HTMLElement;
    const before = dl.textContent;

    /* ⛔ AYNAN MOCK'DAGI SON: «Yangi 120» — 50 qatorli jadval ustida. */
    expect(within(dl).getByText(String(COUNTS.new_count))).toBeTruthy();

    fireEvent.click(loadMoreButton() as HTMLElement);
    await waitFor(() => {
      expect(rowCount(container)).toBe(PAGE_SIZE + SECOND_PAGE_ROWS);
    });

    /*
     * ⛔ YIG'ILIB KETGAN sanoq «Yangi 240» berardi — ya'ni B-6 ni
     *   TESKARI tomondan takrorlardi. Tenglik har ikkala driftda qizaradi.
     */
    expect((container.querySelector("dl") as HTMLElement).textContent).toBe(before);
    expect(
      within(container.querySelector("dl") as HTMLElement).getByText(
        String(COUNTS.new_count),
      ),
    ).toBeTruthy();
  });
});

/* -------------------------------------------------------------------------- */
/* (3) `CASE_PAGE_SIZE` NING HAQIQIY ISTE'MOLCHISI                            */
/* -------------------------------------------------------------------------- */

describe("⛔ B-6 (3): sahifa o'lchami SO'ROVGA yetib boradi", () => {
  test("⛔ birinchi so'rov `limit=50` ni YUBORADI (konstanta o'lik emas)", async () => {
    await renderList();

    const paths = apiClientMock.apiFetch.mock.calls.map(
      (call: unknown[]) => call[0] as string,
    );
    const first = paths.find((path) => path.startsWith("/reconciliation/cases"));

    expect(first).toContain(`limit=${PAGE_SIZE}`);
    /* ⛔ Birinchi sahifada kursor YO'Q — bo'sh kursor yuborilmaydi. */
    expect(first).not.toContain("cursor=");
  });

  test("⛔ ikkinchi so'rov SERVER bergan kursorni O'ZGARISHSIZ qaytaradi", async () => {
    const { container } = await renderList();

    fireEvent.click(loadMoreButton() as HTMLElement);
    await waitFor(() => {
      expect(rowCount(container)).toBe(PAGE_SIZE + SECOND_PAGE_ROWS);
    });

    const paths = apiClientMock.apiFetch.mock.calls.map(
      (call: unknown[]) => call[0] as string,
    );
    const second = paths.find((path) => path.includes("cursor="));

    /*
     * ⛔ KLIENT KURSORNI PARSE QILMAYDI (T-07-123): u serverdan kelgan
     *   satrni faqat URL-kodlab qaytaradi. Da'vo AYNAN o'sha satr ustida.
     */
    expect(second).toContain(`cursor=${encodeURIComponent(CURSOR)}`);
  });
});

/* -------------------------------------------------------------------------- */
/* (4) YUKLANISH — `aria-disabled`, `disabled` EMAS                           */
/* -------------------------------------------------------------------------- */

describe("⛔ B-6 (4): yuklanish davomida FOKUS YO'QOLMAYDI", () => {
  test("⛔ tugma `aria-disabled` bo'ladi va `disabled` atributi QO'YILMAYDI", async () => {
    /* Ikkinchi sahifa — QO'LDA hal qilinadigan va'da (yuklanish ushlanadi). */
    let release: ((value: unknown) => void) | null = null;
    apiClientMock.apiFetch.mockImplementation((path: string) => {
      if (path.includes("cursor=")) {
        return new Promise((resolve) => {
          release = () => resolve(envelope(SECOND_PAGE, null));
        });
      }
      return Promise.resolve(envelope(FIRST_PAGE, CURSOR));
    });

    const { container } = await renderList();

    const button = loadMoreButton() as HTMLElement;
    fireEvent.click(button);

    await waitFor(() => {
      expect(loadMoreButton()?.getAttribute("aria-disabled")).toBe("true");
    });

    /*
     * ⛔ `disabled` EMAS (DL-5 da o'rnatilgan qoida): o'chirilgan tugma
     *   fokusni YO'QOTADI va klaviatura foydalanuvchisi sahifa boshiga
     *   otilib ketardi — aynan yuklanish tugagan lahzada.
     */
    expect(loadMoreButton()?.hasAttribute("disabled")).toBe(false);

    (release as unknown as () => void)();
    await waitFor(() => {
      expect(rowCount(container)).toBe(PAGE_SIZE + SECOND_PAGE_ROWS);
    });
  });

  test("⛔ yuklanish davomida IKKINCHI bosish so'rov QO'SHMAYDI", async () => {
    let release: ((value: unknown) => void) | null = null;
    apiClientMock.apiFetch.mockImplementation((path: string) => {
      if (path.includes("cursor=")) {
        return new Promise((resolve) => {
          release = () => resolve(envelope(SECOND_PAGE, null));
        });
      }
      return Promise.resolve(envelope(FIRST_PAGE, CURSOR));
    });

    const { container } = await renderList();

    fireEvent.click(loadMoreButton() as HTMLElement);
    await waitFor(() => {
      expect(loadMoreButton()?.getAttribute("aria-disabled")).toBe("true");
    });

    /* ⛔ `aria-disabled` bosishni TO'XTATMAYDI — erta `return` to'xtatadi. */
    fireEvent.click(loadMoreButton() as HTMLElement);
    fireEvent.click(loadMoreButton() as HTMLElement);

    const cursorCalls = apiClientMock.apiFetch.mock.calls.filter(
      (call: unknown[]) => (call[0] as string).includes("cursor="),
    );
    expect(cursorCalls).toHaveLength(1);

    (release as unknown as () => void)();
    await waitFor(() => {
      expect(rowCount(container)).toBe(PAGE_SIZE + SECOND_PAGE_ROWS);
    });
  });
});

/* -------------------------------------------------------------------------- */
/* (5) RAD ETILGAN KURSOR — JIM BO'SH SAHIFA EMAS                             */
/* -------------------------------------------------------------------------- */

describe("⛔ B-6 (5): serverning `422` javobi KO'RINADI", () => {
  test("⛔ kursor rad etilganda NOMLANGAN matn chiqadi va mavjud qatorlar QOLADI", async () => {
    apiClientMock.apiFetch.mockImplementation((path: string) => {
      if (path.includes("cursor=")) {
        return Promise.reject(new Error("cursor_invalid"));
      }
      return Promise.resolve(envelope(FIRST_PAGE, CURSOR));
    });

    const { container } = await renderList();

    fireEvent.click(loadMoreButton() as HTMLElement);

    /*
     * ⛔ 07-20 O'LCHAGAN XULQ: buzilgan kursor endi `422` beradi (bazada
     *   u `200` + BO'SH `rows` edi — ya'ni ekran JIMGINA yolg'on
     *   gapirardi). Klient uni ⛔ KO'RSATISHI shart.
     */
    await waitFor(() => {
      expect(container.textContent).toContain(messages.recon.loadMoreFailed);
    });

    /* ⛔ ALLAQACHON KELGAN qatorlar YO'QOLMAYDI — 50 tasi joyida. */
    expect(rowCount(container)).toBe(PAGE_SIZE);

    /* ⛔ Va sanoq ham joyida: blok BUTUNLAY xato holatiga TUSHMAYDI. */
    expect(
      within(container.querySelector("dl") as HTMLElement).getByText(
        String(COUNTS.new_count),
      ),
    ).toBeTruthy();
  });

  test("⛔ BIRINCHI sahifa yiqilganda blok darajasidagi xato matni chiqadi", async () => {
    apiClientMock.apiFetch.mockRejectedValue(new Error("boom"));

    const { container } = await renderList();

    /* ⛔ Ikki xato IKKI XIL matn: biri blok, ikkinchisi sahifa haqida. */
    expect(container.textContent).toContain(messages.errors.loadFailedBody);
    expect(container.textContent).not.toContain(messages.recon.loadMoreFailed);
  });
});

/* -------------------------------------------------------------------------- */
/* (6) WR-08 — SANOQ BLOKI `<dl>` SEMANTIKASINI SAQLAYDI                      */
/* -------------------------------------------------------------------------- */

describe("⛔ WR-08: sanoq bloki `role` bilan ALMASHTIRILMAYDI", () => {
  test("⛔ `<dl>` da `role` atributi YO'Q — `<dt>`/`<dd>` bog'lanishi tirik", async () => {
    const { container } = await renderList();

    const dl = container.querySelector("dl") as HTMLElement;

    /*
     * ⛔ `role="status"` `<dl>` ning implicit rolini ALMASHTIRADI: «Yangi
     *   120 Ko'rilmoqda 7» skrinriderda atama–qiymat bog'lanishini
     *   yo'qotib, oddiy matn oqimiga aylanardi.
     */
    expect(dl.hasAttribute("role")).toBe(false);
    expect(dl.querySelectorAll("dt").length).toBe(4);
    expect(dl.querySelectorAll("dd").length).toBe(4);
  });

  test("⛔ BLOKDA jonli hudud FAQAT yuklanish platsholderida", async () => {
    /*
     * ⛔ Bu blokda foydalanuvchi boshlaydigan yangilash YO'Q, ya'ni jonli
     *   hudud faqat sahifa yuklanganda — HECH KIM KUTMAGAN paytda —
     *   e'lon qilardi.
     */
    const { container } = await renderList();

    expect(container.querySelectorAll('[role="status"]')).toHaveLength(0);
    expect(container.querySelectorAll("[aria-live]")).toHaveLength(0);
  });
});

/* -------------------------------------------------------------------------- */
/* WR-07 — BO'SH HOLAT MATNIDAGI KUN XOM ISO EMAS                             */
/* -------------------------------------------------------------------------- */

test("⛔ WR-07: bo'sh holat matnidagi kun MAHALLIYLASHTIRILGAN", async () => {
  /*
   * ⛔ AYNI MAYDON, UCHTA JOY, UCHTA SHAKL edi (WR-07): bu yerda u xom
   *   ISO bo'lib chizilardi, qo'shni blokda mahalliylashtirilardi.
   *   Foydalanuvchi uchun bu ⛔ IKKI XIL SANA formati — u qaysi biri
   *   «haqiqiy» ekanini so'rashga majbur bo'lardi.
   */
  apiClientMock.apiFetch.mockImplementation(() =>
    Promise.resolve({
      day: DAY,
      rows: [],
      new_count: 0,
      in_review_count: 0,
      justified_count: 0,
      unjustified_count: 0,
      next_cursor: null,
    }),
  );

  const { container } = await renderList();

  const text = container.textContent ?? "";
  expect(text).toContain(messages.recon.emptyCases);
  /* ⛔ Xom `2026-08-11` ekranda YO'Q. */
  expect(text).not.toContain(DAY);
  /* NAZORAT: kun BUTUNLAY yo'qolmagan — u boshqa shaklda turibdi. */
  expect(text).toContain("2026");
});

/* -------------------------------------------------------------------------- */
/* IN-08 — BOZORSIZ SESSIYADA CHEKSIZ SKELET YO'Q                             */
/* -------------------------------------------------------------------------- */

test("⛔ IN-08: `marketId === null` da skelet EMAS, NOMLANGAN holat", () => {
  clearSession();
  setSession({
    accessToken: "t",
    markets: [],
    principal: {
      userId: "33333333-3333-4333-8333-333333333333",
      phone: "+998900000000",
      fullName: "Platforma admini",
      roles: ["director"],
      marketId: null,
      marketName: null,
      isPlatformAdmin: true,
      locale: "uz-Latn",
      mustChangePassword: false,
    },
  });

  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  const { container } = render(
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      timeZone="Asia/Tashkent"
    >
      <QueryClientProvider client={client}>
        <AuthProvider>
          <CaseList day={DAY} />
        </AuthProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>,
  );

  expect(container.querySelectorAll('[aria-busy="true"]')).toHaveLength(0);
  expect(
    within(container).getByText(messages.recon.marketMissing),
  ).toBeInTheDocument();
  expect(apiClientMock.apiFetch).not.toHaveBeenCalled();
});
