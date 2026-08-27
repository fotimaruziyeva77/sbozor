/**
 * ⛔ G-32 (07-UI-SPEC) — MAXRAJSIZ FOIZ YOLG'ON. BESH BAND.
 *
 * =============================================================================
 * ⛔⛔ NEGA BU TEST BOR: RAQAM ROST, XULOSA NOTO'G'RI.
 *
 * Maxrajsiz «68 %» ni direktor «100 tadan 68 tasi» deb o'qiydi. Bu
 * ⛔ KO'RINMAYDIGAN yolg'on — hech qanday typecheck, hech qanday lint va
 * hech qanday «ekran ochiladimi?» testi uni KO'RMAYDI. Uni faqat DOM'da
 * to'rt sanoqning BIRGA turishini o'lchash ushlaydi.
 *
 * ⛔ VA IKKINCHI YARMI UNDAN QIMMATROQ: `0/0` — ⛔ ANIQLANMAGAN, «nol
 *   foiz» EMAS. `0 %` «biz tekshirdik va hech biri asosli chiqmadi»
 *   degan ⛔ TESKARI xulosani berardi, holbuki hech nima hali
 *   tekshirilmagan. Shuning uchun foiz BELGISI ham DOM'da bo'lmasligi
 *   o'lchanadi — «0 ni yashirish» yetarli emas.
 * =============================================================================
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { beforeEach, describe, expect, test, vi } from "vitest";

const apiClientMock = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiClientMock.apiFetch };
});

import messages from "../../../messages/uz-Latn.json";
import { HitRateCard } from "@/components/reconciliation/hit-rate-card";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const DAY = "2026-08-11";

type Counts = {
  justified: number;
  unjustified: number;
  new: number;
  in_review: number;
};

function envelope(counts: Counts) {
  return {
    day: DAY,
    rows: [],
    new_count: counts.new,
    in_review_count: counts.in_review,
    justified_count: counts.justified,
    unjustified_count: counts.unjustified,
    next_cursor: null,
  };
}

/**
 * ⚠ HAR RENDER O'Z `QueryClient` INI OLADI: kesh kaliti sanoqlarni O'Z
 *   ICHIGA OLMAYDI (u faqat bozor va kun bilan doiralangan), ya'ni bir
 *   fayldagi ikkinchi render birinchisining KESHLANGAN javobini darhol
 *   chizardi (07-05 da o'lchangan sinf).
 */
async function renderCard(counts: Counts) {
  apiClientMock.apiFetch.mockResolvedValue(envelope(counts));

  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  const view = render(
    <NextIntlClientProvider locale="uz-Latn" messages={messages} timeZone="Asia/Tashkent">
      <QueryClientProvider client={client}>
        <AuthProvider>
          <HitRateCard day={DAY} />
        </AuthProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>,
  );

  /*
   * ⚠ KUTISH SIGNALI — `aria-busy` NING YO'QOLISHI, formatlangan son EMAS:
   *   `Intl.NumberFormat` uzilmas bo'shliq qo'yadi va Testing Library uni
   *   normalizatsiya qiladi, ya'ni matn bo'yicha kutish MOS KELMASDI
   *   (06-fazada o'lchangan).
   */
  await waitFor(() => {
    expect(view.container.querySelector('[aria-busy="true"]')).toBeNull();
  });

  return view;
}

/** DOM'dagi barcha raqamlar — matn tugunlaridan HOSILA. */
function numbersIn(container: HTMLElement): string[] {
  return (container.textContent ?? "").match(/\d+/gu) ?? [];
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
});

/* -------------------------------------------------------------------------- */
/* (a) FOIZ CHIZILSA — TO'RT SANOQ HAM DOM'DA                                 */
/* -------------------------------------------------------------------------- */

describe("⛔ G-32 (a): foiz KO'RINSA, maxraj ham KO'RINADI", () => {
  test("17 asosli / 8 asossiz -> 68 % VA 17, 25, 8 — TO'RTTASI HAM", async () => {
    const { container } = await renderCard({
      justified: 17,
      unjustified: 8,
      new: 5,
      in_review: 3,
    });

    const numbers = numbersIn(container);

    /*
     * ⛔ TO'RTTASI HAM BIR DA'VODA. Ularni to'rt alohida testga bo'lish
     *   maxraj jumlasini o'chirgan regressiyani BITTA test bilan
     *   qizartirardi va uni «shu ham yetadi» deb o'chirish oson bo'lardi.
     */
    expect(numbers).toContain("68"); // nisbat — 17 / 25
    expect(numbers).toContain("17"); // asosli
    expect(numbers).toContain("25"); // MAXRAJ — hal qilinganlar
    expect(numbers).toContain("8"); // istisno — hali hal qilinmaganlar

    /* Foiz belgisi HAM bor: son yolg'iz «68» bo'lib qolmasin. */
    expect(container.textContent).toMatch(/%|％/u);
  });

  test("⛔ (d) foiz maxraj VA istisno jumlalariga `aria-describedby` bilan bog'langan", async () => {
    const { container } = await renderCard({
      justified: 17,
      unjustified: 8,
      new: 5,
      in_review: 3,
    });

    const percent = container.querySelector("[aria-describedby]");
    expect(percent).not.toBeNull();

    const ids = (percent?.getAttribute("aria-describedby") ?? "").split(/\s+/u);

    /*
     * ⛔ IKKI ID SHART: bittasi bo'lsa skrinrider foydalanuvchisi yo
     *   maxrajni, yo istisnoni eshitmasdi — ya'ni u AYNAN maxrajsiz
     *   foizni eshitardi.
     */
    expect(ids).toHaveLength(2);

    const described = ids
      .map((id) => container.querySelector(`#${CSS.escape(id)}`)?.textContent ?? "")
      .join(" ");

    expect(described).toContain("25"); // maxraj jumlasi
    expect(described).toContain("17"); // asosli
    expect(described).toContain("8"); // istisno jumlasi
  });
});

/* -------------------------------------------------------------------------- */
/* (b) + (c) MAXRAJ NOL — FOIZ UMUMAN YO'Q                                    */
/* -------------------------------------------------------------------------- */

describe("⛔ G-32 (b)/(c): `0/0` — ANIQLANMAGAN, «nol foiz» EMAS", () => {
  test("hal qilingan yo'q -> foiz BELGISI 0 marta va NOMLANGAN sabab bor", async () => {
    const { container } = await renderCard({
      justified: 0,
      unjustified: 0,
      new: 4,
      in_review: 2,
    });

    const text = container.textContent ?? "";

    /* ⛔ Foiz belgisi DOM'da UMUMAN yo'q — «0 ni yashirish» YETARLI EMAS. */
    expect((text.match(/%|％/gu) ?? []).length).toBe(0);

    /* ⛔ Nomlangan sabab MAJBURIY: bo'sh blok «o'lchov buzuq» deb o'qilardi. */
    expect(screen.getByText(messages.recon.accuracyNone)).toBeTruthy();

    /* Navbatdagi sanoq ko'rinadi — 4 + 2 = 6. */
    expect(numbersIn(container)).toContain("6");
  });

  test("⛔ (c) `0`, `NaN`, `Infinity`, `—%` satrlari YO'Q", async () => {
    const { container } = await renderCard({
      justified: 0,
      unjustified: 0,
      new: 4,
      in_review: 2,
    });

    const text = container.textContent ?? "";

    /*
     * ⛔ `NaN` va `Infinity` — `0/0` va `n/0` ning JS dagi tabiiy
     *   natijalari, ya'ni ular «yozib qo'yilgan» emas, BO'LINISHDAN
     *   chiqadi. Ularning yo'qligi shoxning HISOBLAMAGANINI isbotlaydi.
     */
    expect(text).not.toContain("NaN");
    expect(text).not.toContain("Infinity");
    expect(text).not.toContain("—%");

    /* ⛔ Yalang'och `0` ham yo'q: u O'LCHANGAN qiymat ma'nosini berardi. */
    expect(numbersIn(container)).not.toContain("0");
  });

  test("bitta hal qilingan ham foizni TUG'DIRADI (chegara nazorati)", async () => {
    /*
     * ⛔ NAZORAT: yuqoridagi «foiz yo'q» da'vosi shartni `resolved === 0`
     *   dan `resolved < 10` ga o'zgartirgan regressiyada ham yashil
     *   qolardi. Bu test chegarani AYNAN nolga qadaydi.
     */
    const { container } = await renderCard({
      justified: 1,
      unjustified: 0,
      new: 0,
      in_review: 0,
    });

    expect(container.textContent).toMatch(/%|％/u);
    expect(numbersIn(container)).toContain("100");
  });
});

/* -------------------------------------------------------------------------- */
/* WR-05 — YIQILGAN SO'ROV O'LCHANGAN FAKTNI DA'VO QILMAYDI                   */
/* -------------------------------------------------------------------------- */

describe("⛔ WR-05: so'rov YIQILGANDA blok ROST gapiradi", () => {
  /**
   * So'rovni yiqitadi va blokni chizadi.
   *
   * ⛔ `retry: false` MAJBURIY: qayta urinish testni sekinlashtirardi va
   *    `isError` shoxiga yetib borish LAHZASINI noaniq qilardi.
   */
  async function renderFailed() {
    apiClientMock.apiFetch.mockRejectedValue(new Error("tarmoq"));

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
            <HitRateCard day={DAY} />
          </AuthProvider>
        </QueryClientProvider>
      </NextIntlClientProvider>,
    );

    await waitFor(() => {
      expect(view.container.querySelector('[aria-busy="true"]')).toBeNull();
    });

    return view;
  }

  test("⛔ (c) FOIZ BELGISI DOM'da 0 marta va xato `role=\"alert\"` ICHIDA", async () => {
    /*
     * ⛔⛔ NOSOZLIK: yiqilgan so'rovda blok `recon.accuracyNone` ni
     *     chizardi — matni «Hali hal qilingan nomuvofiqlik yo'q».
     *     Bu ⛔ O'LCHANGAN QIYMAT DA'VOSI, holbuki haqiqat «o'lchov
     *     UMUMAN kelmadi». Ikkalasi ⛔ QARAMA-QARSHI xulosa beradi:
     *     birinchisi «navbat toza» deb xotirjam qilardi.
     *
     * ⛔ `null ?? 0` refleksi ham TAQIQ — u aynan shu yolg'onning
     *    arifmetik shakli (05-14: «o'lchanmagan sonning o'rniga NOL
     *    yozilmaydi»).
     */
    const { container } = await renderFailed();

    /* ⛔ FOIZ BELGISI UMUMAN YO'Q — «0 ni yashirish» YETARLI EMAS. */
    expect(((container.textContent ?? "").match(/%|％/gu) ?? []).length).toBe(0);

    /* ⛔ XATO HOLATI KO'RINADI va u E'LON QILINADI. */
    const alert = container.querySelector('[role="alert"]');
    expect(alert).not.toBeNull();
    expect(alert?.textContent).toContain(messages.errors.loadFailedBody);

    /* ⛔ VA O'LCHANGAN FAKT DA'VOSI YO'Q. */
    expect(container.textContent).not.toContain(messages.recon.accuracyNone);

    /* ⛔ `0`, `NaN`, `Infinity` — hech biri chizilmaydi. */
    expect(numbersIn(container)).toEqual([]);
    expect(container.textContent).not.toContain("NaN");
    expect(container.textContent).not.toContain("Infinity");
  });

  test("⛔ mazmun atributi YIQILGAN holatda ham TURADI", async () => {
    /*
     * ⛔ Sahifa darvozasi blok to'plamini TENGLIK bilan o'lchaydi:
     *   xatoda atributning yo'qolishi «blok chizilmadi» degan BOSHQA
     *   nosozlik bo'lib ko'rinardi.
     */
    const { container } = await renderFailed();

    expect(
      container.querySelector('[data-recon-content="hitrate"]'),
    ).not.toBeNull();
  });

  test("MUVAFFAQIYATLI so'rovda `accuracyNone` HAMON chiziladi (nazorat)", async () => {
    /*
     * ⛔ NAZORAT MAJBURIY: `accuracyNone` ni BUTUNLAY olib tashlagan
     *   regressiya yuqoridagi testni yashil qoldirardi — holbuki
     *   «maxraj nol» shoxida u AYNAN to'g'ri matn.
     */
    const { container } = await renderCard({
      justified: 0,
      unjustified: 0,
      new: 4,
      in_review: 2,
    });

    expect(container.textContent).toContain(messages.recon.accuracyNone);
    expect(container.querySelector('[role="alert"]')).toBeNull();
  });
});

/* -------------------------------------------------------------------------- */
/* (e) NISBAT SAQLANMAYDI                                                     */
/* -------------------------------------------------------------------------- */

test("⛔ G-32 (e): nisbat MAYDON NOMI sifatida kodda yo'q", async () => {
  /*
   * ⛔ Bu band `scripts/reconciliation-copy.test.mjs` da KATALOG
   *   darajasida ham o'lchanadi; bu yerda esa u KOMPONENT faylining
   *   O'ZIDA takrorlanadi, chunki aynan shu fayl nisbatni hisoblaydi va
   *   uni o'zgaruvchiga yozish vasvasasi AYNAN shu yerda tug'iladi.
   */
  /*
   * ⚠ `import.meta.url` vite transformidan keyin `file:` sxemasida EMAS —
   *   yo'l `process.cwd()` dan quriladi (07-05 da o'lchangan sinf).
   *   ⛔ Fayl topilmasa test `throw` qiladi, jim o'tmaydi.
   */
  const { existsSync, readFileSync } = await import("node:fs");
  const { join } = await import("node:path");

  const file = join(
    process.cwd(),
    "src",
    "components",
    "reconciliation",
    "hit-rate-card.tsx",
  );
  if (!existsSync(file)) throw new Error(`komponent fayli topilmadi: ${file}`);

  const source = readFileSync(file, "utf8");

  expect(source).not.toContain("hit_rate");
  expect(source).not.toContain("hitRate");
});

/* -------------------------------------------------------------------------- */
/* IN-08 — BOZORSIZ SESSIYADA CHEKSIZ SKELET YO'Q                             */
/* -------------------------------------------------------------------------- */

test("⛔ IN-08: `marketId === null` da skelet EMAS, NOMLANGAN holat", () => {
  /*
   * ⛔ TanStack v5 da O'CHIRILGAN so'rov `isPending` holatida QOLADI —
   *   ya'ni bu karta bozorsiz sessiyada ABADIY skelet ko'rsatardi.
   *   `HeadlineCard` bu holatni ochiq qo'riqlaydi (`marketId === null`
   *   -> so'rov ham, karta ham yo'q); recon bloklari esa yo'q edi.
   */
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
          <HitRateCard day={DAY} />
        </AuthProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>,
  );

  expect(container.querySelectorAll('[aria-busy="true"]')).toHaveLength(0);
  expect(container.textContent).toContain(messages.recon.marketMissing);

  /* ⛔ VA FOIZ BELGISI HAM YO'Q: o'lchov umuman boshlanmagan. */
  expect((container.textContent ?? "").match(/%|％/gu) ?? []).toHaveLength(0);
  expect(apiClientMock.apiFetch).not.toHaveBeenCalled();

  /* ⛔ Mazmun atributi HAR holatda — sahifa darvozasi uni to'plamda kutadi. */
  expect(container.querySelector('[data-recon-content="hitrate"]')).not.toBeNull();
});
