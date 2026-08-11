/**
 * ⛔⛔ G-20 (06-UI-SPEC §8.2) — ≤3 O'ZARO TA'SIR, DOM'DAN HOSILA SANOQ.
 *
 * =============================================================================
 * ⛔ 1. NEGA SANOQ, «UCHTA TUGMA BOR» EMAS.
 *
 *   Strukturaviy tekshiruv («qidiruv maydoni bor, radiogroup bor, tasdiq
 *   bor») to'rtinchi qadam qo'shilganda YASHIL qolardi. Sanoq esa 4 ni
 *   qaytaradi va HECH KIM ro'yxatni yangilamasdan test qizaradi. Bu
 *   D-32 ning UI shakli: qamrov HOSILA, qo'lda yozilgan ro'yxat emas.
 *
 * ⛔ 2. TENGLIK, «KATTA EMAS» SHAKLIDAGI DA'VO EMAS.
 *
 *   Sanoq 2 ga TUSHSA ham test qizarishi kerak: 2 qadam degani
 *   tasdiqlash AVTOMATIK bo'lgan, ya'ni ⛔ TASDIQSIZ PUL YOZILGAN.
 *   «≤3» — talab matnining chegarasi; o'lchovning maqsadi AYNAN 3, va
 *   shuning uchun bu faylda yuqori chegara shaklidagi matcher UMUMAN
 *   ishlatilmaydi (grep bilan o'lchanadi).
 *
 * ⛔ 3. `visited` DOM'DAN YIG'ILADI, TESTDA E'LON QILINMAYDI.
 *
 *   Faqat KUTILGAN NATIJA yozilgan. Ro'yxatni testda qurish uni «model
 *   o'ziga teng» tavtologiyasiga aylantirardi (06-08 ning darsi).
 *
 * ⛔ 4. §8.2 FLAG'INING QARORI SHU YERDA O'LCHANADI.
 *
 *   Ko'p moslikdagi tanlash 1-QADAM ICHIDA qoladi: qadam identifikatori
 *   `"stall"` bo'lib turadi, sanoq esa 4 ni ko'rsatadi. Ya'ni qo'shimcha
 *   o'zaro ta'sir YASHIRILMAYDI — u SON bilan ko'rinadi va 02-UI-SPEC
 *   §6.9 ning «≤2 o'zaro ta'sir» byudjeti o'lchanadigan bo'ladi.
 *
 * ⛔ 5. IKKINCHI TAKROR HAM AYNAN 3 (§8.5).
 *
 *   Kassirning kuni — bitta oqim emas, uning 300–1000 marta takrori.
 *   Fokus qaytmasa real sanoq 4 ga chiqardi va D-18 rasmiy ravishda
 *   bajarilib, AMALDA buzilgan bo'lardi.
 * =============================================================================
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
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

import messages from "../../../messages/uz-Latn.json";
import { CollectSession } from "@/components/collect/collect-session";
import { ApiError } from "@/lib/api-client";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const SHIFT_ID = "22222222-2222-4222-8222-222222222222";
const PAYMENT_ID = "33333333-3333-4333-8333-333333333333";

const OPEN_SHIFT = {
  id: SHIFT_ID,
  status: "open",
  opened_at: "2026-09-14T02:00:00Z",
};

/** ⛔ Server bergan proyeksiya — summa TESTDA hisoblanmaydi. */
const PENDING = {
  stall_code: "14-C",
  service_date: "2026-09-14",
  market_open: true,
  amount_soum: 15_000,
  amount_unavailable_reason: null,
  outstanding_soum: 0,
  total_due_soum: 15_000,
};

const SECOND_PENDING = { ...PENDING, stall_code: "15-A" };

/** ⛔ Ko'p moslik — server FAQAT kodlarni beradi, summani EMAS. */
const MULTI = { matches: ["10", "100"], stall: null };

const WRITTEN = {
  payment_id: PAYMENT_ID,
  stall_code: "14-C",
  service_date: "2026-09-14",
  amount_soum: 15_000,
  kind: "payment",
  method: "cash",
  created_at: "2026-09-14T06:00:00Z",
  reversed: false,
};

let client: QueryClient;

function seedSession(): void {
  setSession({
    accessToken: "test-access-token",
    principal: {
      userId: "44444444-4444-4444-8444-444444444444",
      phone: "+998900000000",
      fullName: "Test Cashier",
      roles: ["cashier"],
      marketId: MARKET_ID,
      marketName: "Karmana markaziy bozori",
      isPlatformAdmin: false,
      locale: "uz-Latn",
      mustChangePassword: false,
    },
    markets: [],
  });
}

/** Yo'l bo'yicha javob beradigan mock — ro'yxat SHART bo'yicha tanlanadi. */
function routeFetch(pendingFor: Record<string, unknown>): void {
  apiClientMock.apiFetch.mockImplementation(
    (path: string, options?: { method?: string }) => {
      if (path === "/shifts/open") return Promise.resolve(OPEN_SHIFT);
      /* ⛔ Oyna SERVERDA qat'iy — bu yerda ham bo'sh javob YETARLI. */
      if (path === "/payments/recent") return Promise.resolve({ items: [] });
      if (path === "/payments" && options?.method === "POST") {
        return Promise.resolve(WRITTEN);
      }
      if (path.startsWith("/billing/pending?stall_code=")) {
        const code = decodeURIComponent(path.split("=")[1]);
        const answer = pendingFor[code];
        if (answer === undefined) {
          return Promise.reject(new Error(`kutilmagan kod: ${code}`));
        }
        return Promise.resolve(answer);
      }
      return Promise.reject(new Error(`mock'lanmagan yo'l: ${path}`));
    },
  );
}

function renderSession() {
  return render(
    <QueryClientProvider client={client}>
      <AuthProvider>
        <NextIntlClientProvider
          locale="uz-Latn"
          messages={messages}
          timeZone="Asia/Tashkent"
        >
          <CollectSession shiftHref="/uz/collect/shift" />
        </NextIntlClientProvider>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

/* -------------------------------------------------------------------------- */
/* SIKL — §8.2 DAGI SHAKLNING AYNAN O'ZI                                      */
/* -------------------------------------------------------------------------- */

function stepElements(): HTMLElement[] {
  return Array.from(
    document.querySelectorAll<HTMLElement>("[data-collect-step]"),
  );
}

/**
 * Elementning «hozirgi qiyofasi» — sikl SILJIGANINI aniqlash uchun.
 *
 * ⚠ Faqat `data-collect-step` qiymati YETARLI EMAS: ko'p moslik yo'lida
 *   ikkinchi qadam ham `"stall"` (bu §8.2 FLAG'ining qarori), ya'ni
 *   qiymatga qarab kutish siklni MUZLATIB qo'yardi.
 */
function stepKey(el: HTMLElement): string {
  return `${el.dataset.collectStep}|${el.tagName}|${(el.textContent ?? "").slice(0, 40)}`;
}

/**
 * ⛔ HOSILA HARAKAT: element O'ZI qanday ta'sir kutayotganini aytadi.
 *
 *   - tanlov variantlari bor (`[data-collect-option]`) -> birinchisini bosish
 *     (ko'p moslik ro'yxati HAM, radiogroup HAM shu shoxdan o'tadi);
 *   - matn maydoni                                     -> terish + `Enter`;
 *   - qolgani                                          -> bosish.
 */
function actOn(el: HTMLElement, code: string): void {
  const option = el.querySelector<HTMLElement>("[data-collect-option]");
  if (option !== null) {
    fireEvent.click(option);
    return;
  }
  if (el instanceof HTMLInputElement) {
    fireEvent.change(el, { target: { value: code } });
    fireEvent.keyDown(el, { key: "Enter" });
    return;
  }
  fireEvent.click(el);
}

function paymentCalls(): [string, { body: Record<string, unknown> }][] {
  return (
    apiClientMock.apiFetch.mock.calls as [
      string,
      { method?: string; body: Record<string, unknown> },
    ][]
  ).filter(([path, options]) => path === "/payments" && options.method === "POST");
}

/** ⛔ SANOQ SHU YERDA TUG'ILADI — DOM'dan, ro'yxatdan emas. */
async function runFlow(code: string) {
  const before = paymentCalls().length;
  const posted = () => paymentCalls().length > before;

  const visited: string[] = [];
  let steps = 0;

  await waitFor(() => expect(stepElements()).toHaveLength(1));

  while (!posted() && steps < 10) {
    const els = stepElements();
    /* (a) ⛔ NOANIQLIK YO'Q: bir vaqtda ikkita asosiy element bo'lmaydi. */
    expect(els).toHaveLength(1);

    const el = els[0];
    visited.push(el.dataset.collectStep ?? "");
    const marker = stepKey(el);

    actOn(el, code);
    steps += 1;

    /*
     * ⛔ ORALIQ HOLATDA HARAKAT QILINMAYDI. Faqat «qiyofa o'zgardimi?»
     *   deb kutish YETMAYDI: ko'p moslikda ro'yxat bosilgan zahoti u
     *   yo'qoladi va qadam BIR LAHZAGA yana qidiruv maydoniga qaytadi —
     *   sikl o'sha lahzada kodni QAYTA terib, ro'yxatni qayta ochardi va
     *   sanoq 10 ga yetib to'xtardi. Shuning uchun sikl so'rov va
     *   mutatsiya TUGAGUNCHA kutadi.
     */
    await waitFor(() => {
      expect(client.isFetching()).toBe(0);
      expect(client.isMutating()).toBe(0);

      const next = stepElements();
      expect(next).toHaveLength(1);
      expect(stepKey(next[0])).not.toBe(marker);
    });
  }

  return { posted: posted(), steps, visited };
}

/* -------------------------------------------------------------------------- */

describe("G-20 (06-UI-SPEC §8.2): qadam sanog'i", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    clearSession();
    seedSession();
    client = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
  });

  afterEach(() => {
    client.clear();
    clearSession();
  });

  test("⛔ BAXTLI YO'L: sahifadan `POST /payments` gacha AYNAN 3 qadam", async () => {
    routeFetch({ "14-C": PENDING });
    renderSession();

    const { posted, steps, visited } = await runFlow("14-C");

    expect(posted).toBe(true);
    /* (b) ⛔ AYNAN uch — 2 ham, 4 ham qizil. */
    expect(steps).toBe(3);
    /* (c) tartib + to'plam tengligi. */
    expect(visited).toEqual(["stall", "method", "confirm"]);
  });

  test("⛔ POST tanasidagi summa SERVER bergan qiymatga TENG (D-20)", async () => {
    routeFetch({ "14-C": PENDING });
    renderSession();

    await runFlow("14-C");

    const [, options] = paymentCalls()[0];
    /* ⛔ Kutilgan qiymat MOCK JAVOBIDAN olinadi — literal yozilmaydi. */
    expect(options.body.amount_soum).toBe(PENDING.amount_soum);
    expect(options.body.stall_code).toBe(PENDING.stall_code);
    expect(options.body.method).toBe("cash");
    /* ⛔ `shift_id` YUBORILMAYDI — serverning o'zi yechadi (06-09, T-06-57). */
    expect(Object.hasOwn(options.body, "shift_id")).toBe(false);
    /* ⛔ Server taklifiga teng summa sabab-kod TALAB QILMAYDI. */
    expect(Object.hasOwn(options.body, "reason_code")).toBe(false);
  });

  test("⛔ KO'P MOSLIK: sanoq 4, va qo'shimcha qadam 1-QADAM ICHIDA", async () => {
    /*
     * Server `"1"` uchun FAQAT kodlar ro'yxatini beradi (summa yo'q),
     * tanlangandan keyin esa tekis proyeksiyani.
     */
    routeFetch({ "1": MULTI, "10": { ...PENDING, stall_code: "10" } });
    renderSession();

    const { posted, steps, visited } = await runFlow("1");

    expect(posted).toBe(true);
    expect(steps).toBe(4);
    expect(visited).toEqual(["stall", "stall", "method", "confirm"]);
    /*
     * ⛔ IKKALA YO'LDA HAM qadam TURLARI to'plami bir xil: uchta tur va
     *    boshqasi yo'q. Ya'ni ko'p moslik YANGI qadam TURI qo'shmaydi.
     */
    expect(new Set(visited)).toEqual(
      new Set(["stall", "method", "confirm"]),
    );
  });

  test("⛔ IKKINCHI TAKROR HAM AYNAN 3 — fokus qidiruvga QAYTADI (§8.5)", async () => {
    routeFetch({ "14-C": PENDING, "15-A": SECOND_PENDING });
    renderSession();

    const first = await runFlow("14-C");
    expect(first.steps).toBe(3);

    const second = await runFlow("15-A");

    expect(second.posted).toBe(true);
    expect(second.steps).toBe(3);
    expect(second.visited).toEqual(["stall", "method", "confirm"]);
  });

  test("⛔ to'lovdan keyin FOKUS qidiruv maydonida va maydon BO'SH", async () => {
    routeFetch({ "14-C": PENDING });
    const { container } = renderSession();

    await runFlow("14-C");

    await waitFor(() => {
      const input = container.querySelector<HTMLInputElement>(
        'input[data-collect-step="stall"]',
      );
      expect(input).not.toBeNull();
      expect(input?.value).toBe("");
      expect(document.activeElement).toBe(input);
    });
  });

  test("ochiq smena yo'q bo'lsa to'lov yuzasi UMUMAN chizilmaydi", async () => {
    apiClientMock.apiFetch.mockImplementation((path: string) => {
      if (path === "/shifts/open") return Promise.resolve(null);
      if (path === "/payments/recent") return Promise.resolve({ items: [] });
      return Promise.reject(new Error(`kutilmagan yo'l: ${path}`));
    });

    const { container } = renderSession();

    await waitFor(() => {
      expect(
        container.querySelectorAll("[data-collect-step]"),
      ).toHaveLength(0);
    });
    expect(
      container.querySelector('a[href="/uz/collect/shift"]'),
    ).not.toBeNull();
  });

  /*
   * ==========================================================================
   * ⛔⛔ CR-04 — 404 `stall_not_found` NING KLIENT YARMI.
   *
   * Server bu kodni LUG'AT `detail` bilan yuborardi
   * (`{"error_code": "stall_not_found"}`), `api-client.ts::detailOf()` esa
   * `detail` ni FAQAT satr bo'lganda o'qiydi — ya'ni `ApiError.detail` `""`
   * bo'lib qolardi va:
   *
   *     `collect-session.tsx::notFound`            -> HAR DOIM `false`
   *     `collectState()` ning `"not-found"` holati -> O'LIK KOD
   *     `StallLookup` ning «Rasta topilmadi» shoxi -> HECH QACHON
   *
   * Kassir esa `errors.loadFailedTitle` + [Qayta urinish] ko'rardi va har
   * urinish o'sha 404 ni qaytarardi. Klient kodi TO'G'RI edi — u kodni
   * hech qachon OLMAGANDI.
   *
   * ⛔ TEST SERVER SHAKLIDAN EMAS, `ApiError` DAN YURADI: bu qatlamning
   *    kontrakti aynan shu. Server yarmi
   *    `test_billing_api.py::test_an_unknown_code_is_not_an_empty_list` va
   *    `test_route_coverage.py` ning AST darvozasi bilan o'lchanadi.
   * ==========================================================================
   */
  test("⛔ CR-04: 404 `stall_not_found` SABAB+YECHIM juftligini chizadi", async () => {
    apiClientMock.apiFetch.mockImplementation((path: string) => {
      if (path === "/shifts/open") return Promise.resolve(OPEN_SHIFT);
      if (path === "/payments/recent") return Promise.resolve({ items: [] });
      if (path.startsWith("/billing/pending?stall_code=")) {
        return Promise.reject(new ApiError(404, "stall_not_found"));
      }
      return Promise.reject(new Error(`mock'lanmagan yo'l: ${path}`));
    });

    const { container } = renderSession();

    const input = await waitFor(() => {
      const el = container.querySelector<HTMLInputElement>("input[data-collect-step]");
      expect(el).not.toBeNull();
      return el as HTMLInputElement;
    });
    fireEvent.change(input, { target: { value: "99999" } });
    fireEvent.keyDown(input, { key: "Enter" });

    const cause = messages.collect.errorCause.stall_not_found;
    const fix = messages.collect.errorFix.stall_not_found;

    await waitFor(() => {
      expect(client.isFetching()).toBe(0);
      expect(container.textContent).toContain(cause);
      expect(container.textContent).toContain(fix);
    });

    /*
     * ⛔ IKKINCHI YARIM — TO'PLAM TENGLIGI, INKOR TASDIQ EMAS (D-31).
     *
     *   «Topilmadi» bloki `role="status"` (qayta terish holati), umumiy
     *   yuklash xatosi esa `role="alert"` (`pending-card.tsx:126`). Nuqson
     *   paytida AYNAN ikkinchisi chizilardi. `not.toContain(matn)` faqat
     *   o'sha satrni ushlardi; `role="alert"` to'plamining BO'SHLIGI esa
     *   «bu shoxda birorta ogohlantiruvchi blok yo'q» degan KUCHLIROQ
     *   da'vo — kelajakda boshqa nomli xato bloki qo'shilsa ham qizaradi.
     */
    const alerts = Array.from(
      container.querySelectorAll<HTMLElement>('[role="alert"]'),
    ).map((el) => el.textContent ?? "");
    expect(alerts).toEqual([]);
  });
});
